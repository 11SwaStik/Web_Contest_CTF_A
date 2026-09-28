"""Smoke + challenge tests for the contest app.

Run with:  pytest -q
"""
import base64
import json

FLAG_Q1 = "FLAG{scaler_un10n_sql1_r3c0n_a1}"
FLAG_Q2 = "FLAG{scaler_jwt_n0ne_alg_esc_a2}"
FLAG_Q3 = "FLAG{scaler_b0la_id_3num_ap1_a3}"
API_TOKEN = "db_live_sk_demo_7c3f9a2b1e"


def _b64(obj):
    return base64.urlsafe_b64encode(
        json.dumps(obj, separators=(",", ":")).encode()
    ).rstrip(b"=").decode()


# ---------- Store: normal behaviour works ----------

def test_stale_db_is_rebuilt(tmp_path):
    # A pre-existing DB with an older `users` schema must not crash the app;
    # init_db detects the drift and rebuilds from scratch.
    import os, sqlite3, importlib
    dbfile = tmp_path / "stale.db"
    con = sqlite3.connect(dbfile)
    con.executescript("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, "
                       "password_hash TEXT, role TEXT, full_name TEXT);")
    con.execute("INSERT INTO users (username,password_hash,role,full_name) "
                "VALUES ('alice','x','member','Alice')")
    con.commit(); con.close()

    os.environ["DB_PATH"] = str(dbfile)
    import app.config, app.db
    importlib.reload(app.config); importlib.reload(app.db)
    app.db.init_db()
    user = app.db.get_user("alice")
    assert user and user["email"] and user["plan"]  # reseeded with new columns


def test_briefing_page(client):
    body = client.get("/").data.decode()
    assert "Security Assessment" in body
    assert "Voltix" in body  # target listed by brand name
    # No vulnerability-type labels leak on the wrapper.
    assert "SQL Injection" not in body
    assert "BOLA" not in body


def test_store_home(client):
    body = client.get("/shop").data.decode()
    assert "Top rated" in body
    assert "Mechanical Keyboard" in body


def test_category_browse(client):
    body = client.get("/shop?category=audio").data.decode()
    assert "Headphones" in body


def test_unknown_category_404(client):
    assert client.get("/shop?category=does-not-exist").status_code == 404


def test_product_detail(client):
    body = client.get("/shop/product/2").data.decode()
    assert "Add to cart" in body


def test_product_missing_404(client):
    assert client.get("/shop/product/99999").status_code == 404


def test_about_and_health(client):
    assert "About Voltix" in client.get("/shop/about").data.decode()
    assert client.get("/healthz").get_json() == {"status": "ok"}


def test_benign_search(client):
    body = client.get("/shop?q=mouse").data.decode()
    assert "Wireless Mouse" in body


# ---------- Q1 challenge: the search is injectable ----------

def test_search_is_injectable(client):
    # A stray quote surfaces a DB error (error-based feedback).
    body = client.get("/shop?q='").data.decode()
    assert "went wrong" in body


def test_flag_not_leaked_normally(client):
    # The flag must never appear during ordinary use.
    for path in ["/", "/shop", "/shop?q=keyboard", "/shop/product/1"]:
        assert FLAG_Q1 not in client.get(path).data.decode()


def test_union_injection_recovers_flag(client):
    payload = ("zzz%' UNION SELECT id, flag_value, note, 0, 'Secret', '!', 5 "
               "FROM internal_flags-- ")
    body = client.get("/shop", query_string={"q": payload}).data.decode()
    assert FLAG_Q1 in body


# ---------- Voltix commerce: real app must actually work ----------

def test_product_page_has_specs_and_reviews(client):
    body = client.get("/shop/product/2").data.decode()
    assert "Specifications" in body and "Customer reviews" in body


def test_browse_sort_and_filter(client):
    r = client.get("/shop?category=audio&sort=price_desc&in_stock=1")
    assert r.status_code == 200


def test_cart_and_checkout_flow(client):
    client.post("/shop/cart/add", data={"product_id": "2", "qty": "2"})
    client.post("/shop/cart/add", data={"product_id": "10", "qty": "1"})
    cart = client.get("/shop/cart").data.decode()
    assert cart.count("cartrow__name") == 2

    r = client.post("/shop/checkout", data={
        "full_name": "Test User", "email": "t@e.com", "address": "1 St",
        "city": "Town", "postcode": "12345"}, follow_redirects=True)
    body = r.data.decode()
    assert "confirmed" in body
    import re
    assert re.search(r"VLT-\d{8}", body)
    # cart emptied after ordering
    assert client.get("/shop/cart").data.decode().count("cartrow__name") == 0


def test_checkout_requires_nonempty_cart(client):
    r = client.get("/shop/checkout", follow_redirects=True)
    assert "empty" in r.data.decode()


def test_newsletter_decoy_works(client):
    r = client.post("/shop/newsletter", data={"email": "a@b.com"},
                    follow_redirects=True)
    assert "subscribing" in r.data.decode()


def test_contact_decoy_works(client):
    r = client.post("/shop/contact",
                    data={"name": "A", "email": "a@b.com", "message": "hi"},
                    follow_redirects=True)
    assert "get back to you" in r.data.decode()


def test_static_pages(client):
    for p in ["/shop/shipping", "/shop/returns", "/shop/contact"]:
        assert client.get(p).status_code == 200


# ---------- Q2 challenge: JWT alg:none privilege escalation ----------

def test_portal_login_required(client):
    # Dashboard without a session redirects to login.
    assert client.get("/portal/dashboard").status_code == 302


def test_portal_bad_login(client):
    body = client.post("/portal/login",
                       data={"username": "alice", "password": "nope"}).data.decode()
    assert "Invalid" in body


def test_portal_member_cannot_reach_admin(client):
    client.post("/portal/login",
                data={"username": "alice", "password": "member2026"})
    r = client.get("/portal/admin")
    assert r.status_code == 403
    assert FLAG_Q2 not in r.data.decode()


def test_portal_alg_none_forgery_grants_flag(client):
    forged = _b64({"alg": "none", "typ": "JWT"}) + "." + \
             _b64({"sub": "alice", "role": "admin"}) + "."
    client.set_cookie("session_token", forged)
    body = client.get("/portal/admin").data.decode()
    assert FLAG_Q2 in body


def test_portal_wrong_secret_rejected(client):
    import hmac, hashlib
    h = _b64({"alg": "HS256", "typ": "JWT"})
    p = _b64({"sub": "alice", "role": "admin"})
    sig = base64.urlsafe_b64encode(
        hmac.new(b"wrong-secret", f"{h}.{p}".encode(), hashlib.sha256).digest()
    ).rstrip(b"=").decode()
    client.set_cookie("session_token", f"{h}.{p}.{sig}")
    r = client.get("/portal/admin")
    assert r.status_code == 302  # rejected -> redirected to login
    assert FLAG_Q2 not in r.data.decode()


# ---------- Meridian: the portal must be a real, working SaaS ----------

def _login(client, u="alice", pw="member2026"):
    return client.post("/portal/login", data={"username": u, "password": pw})


def test_portal_landing_public(client):
    body = client.get("/portal").data.decode()
    assert "Sign in" in body and "Pricing" in body


def test_portal_dashboard_shows_account_data(client):
    _login(client)
    body = client.get("/portal/dashboard").data.decode()
    assert "Alice Turner" in body and "Northwind Traders" in body and "Pro" in body


def test_portal_billing_and_invoice_scoping(client):
    _login(client)
    assert "INV-2026-0412" in client.get("/portal/billing").data.decode()
    # own invoice viewable
    assert client.get("/portal/billing/invoice/INV-2026-0412").status_code == 200
    # another user's invoice is not (scoped, not IDOR)
    assert client.get("/portal/billing/invoice/INV-2026-0410").status_code == 404


def test_portal_team_list(client):
    _login(client)
    assert "Chidi Okafor" in client.get("/portal/team").data.decode()


def test_portal_settings_profile_persists(client):
    _login(client)
    client.post("/portal/settings/profile",
                data={"full_name": "Alice Updated", "email": "a2@northwind.example"})
    assert "Alice Updated" in client.get("/portal/settings").data.decode()


def test_portal_password_change(client):
    _login(client)
    r = client.post("/portal/settings/password",
                    data={"current": "member2026", "new": "newpass123"},
                    follow_redirects=True)
    assert "changed" in r.data.decode()
    client.get("/portal/logout")
    # old password now rejected (failed login re-renders with an error)
    assert "Invalid" in _login(client).data.decode()
    # new password works
    assert _login(client, pw="newpass123").status_code == 302


def test_portal_change_plan_persists(client):
    _login(client)
    client.post("/portal/billing/plan", data={"plan": "Enterprise"})
    assert "Enterprise" in client.get("/portal/billing").data.decode()


def test_portal_update_card(client):
    _login(client)
    r = client.post("/portal/billing/card",
                    data={"number": "4242 4242 4242 4242", "expiry": "08/28"},
                    follow_redirects=True)
    assert "saved" in r.data.decode()


def test_portal_invoice_download(client):
    _login(client)
    r = client.get("/portal/billing/invoice/INV-2026-0412/download")
    assert r.status_code == 200
    assert "attachment" in r.headers.get("Content-Disposition", "")
    assert b"TOTAL" in r.data


def test_portal_team_invite_adds_member(client):
    _login(client)
    client.post("/portal/team/invite",
                data={"name": "Eve Stone", "email": "eve@northwind.example"})
    assert "Eve Stone" in client.get("/portal/team").data.decode()


def test_portal_notifications_save(client):
    _login(client)
    r = client.post("/portal/settings/notifications", data={}, follow_redirects=True)
    assert "preferences saved" in r.data.decode()



# ---------- Q3 challenge: API BOLA / IDOR ----------

def _auth():
    return {"Authorization": f"Bearer {API_TOKEN}"}


def test_api_landing_and_docs(client):
    assert "DataBridge" in client.get("/api").data.decode()
    docs = client.get("/api/docs").data.decode()
    assert "API Reference" in docs
    assert API_TOKEN in docs  # sandbox key shown to developers


def test_api_usage_decoy(client):
    # Decoy endpoint: works with auth, 401 without, never contains the flag.
    assert client.get("/api/v1/usage").status_code == 401
    r = client.get("/api/v1/usage", headers={"Authorization": f"Bearer {API_TOKEN}"})
    assert r.status_code == 200
    assert FLAG_Q3 not in r.data.decode()


def test_api_requires_token(client):
    assert client.get("/api/v1/accounts/1007").status_code == 401
    assert client.get("/api/v1/accounts/1007",
                      headers={"Authorization": "Bearer nope"}).status_code == 401


def test_api_me_returns_own_account(client):
    j = client.get("/api/v1/accounts/me", headers=_auth()).get_json()
    assert j["id"] == 1007


def test_api_bola_reads_other_account_flag(client):
    r = client.get("/api/v1/accounts/1000", headers=_auth())
    assert r.status_code == 200
    assert r.get_json()["private_note"] == FLAG_Q3


def test_api_flag_not_leaked_without_auth(client):
    # The flag must not be reachable unauthenticated.
    r = client.get("/api/v1/accounts/1000")
    assert r.status_code == 401
    assert FLAG_Q3 not in r.data.decode()


def test_api_events_decoy(client):
    assert client.get("/api/v1/events").status_code == 401
    j = client.get("/api/v1/events", headers=_auth()).get_json()
    assert j["object"] == "list" and FLAG_Q3 not in str(j)


def test_api_health_public(client):
    j = client.get("/api/v1/health").get_json()
    assert j["status"] == "operational"


def test_api_dashboard(client):
    body = client.get("/api/dashboard").data.decode()
    assert API_TOKEN in body           # sandbox key shown
    assert "1007" in body              # account id shown
    assert FLAG_Q3 not in body         # flag never on the dashboard
