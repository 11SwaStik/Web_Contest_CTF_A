"""Q2 — Auth & Session Attacks (Set A): the Meridian customer portal.

Meridian is a business SaaS portal: marketing site, sign-in, a dashboard, and
real billing / team / settings areas. Login and password checks are safe. The
one intentional flaw is in **session token verification**: the portal issues a
JWT for the session, but the verifier **accepts `alg: none`** (an unsigned
token). So a logged-in member can forge a token with `role: admin` and reach the
admin panel, where the flag lives.

Intended path (no cracking needed):
  1. Sign in with the member account from the prompt.
  2. Inspect the `session_token` cookie — a JWT: header.payload.signature.
  3. Forge an unsigned token with `"role":"admin"` (`alg:none`, empty signature).
  4. Load /portal/admin → the flag.

Intentionally vulnerable code for an authorised training contest — do not fix
the token verifier.
"""
import base64
import hashlib
import hmac
import json

from flask import (Blueprint, request, render_template, redirect, url_for,
                   make_response, flash, abort, Response)

from .. import db

bp = Blueprint("auth", __name__, url_prefix="/portal")

# Server secret for signing legitimate tokens. Strong + unknown to students, so
# the HS256 path can't be forged by guessing — the intended flaw is `alg:none`.
_JWT_SECRET = b"portal-signing-key-4e9f1c77c0b84c2ea1"

AUTH_FLAG_A = "FLAG{scaler_jwt_n0ne_alg_esc_a2}"


# --- Minimal JWT (intentionally flawed verifier) --------------------------

def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64url_decode(seg: str) -> bytes:
    return base64.urlsafe_b64decode(seg + "=" * (-len(seg) % 4))


def issue_token(username: str, role: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": username, "role": role}
    h = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    sig = hmac.new(_JWT_SECRET, f"{h}.{p}".encode(), hashlib.sha256).digest()
    return f"{h}.{p}.{_b64url_encode(sig)}"


def verify_token(token: str):
    """Return the payload if the token is 'valid', else None.

    INTENTIONAL VULNERABILITY: `alg: none` tokens are accepted with no signature.
    """
    try:
        h_seg, p_seg, sig_seg = token.split(".")
        header = json.loads(_b64url_decode(h_seg))
        payload = json.loads(_b64url_decode(p_seg))
    except Exception:
        return None
    alg = header.get("alg")
    if alg == "none":
        return payload  # <-- VULN
    if alg == "HS256":
        expected = hmac.new(_JWT_SECRET, f"{h_seg}.{p_seg}".encode(), hashlib.sha256).digest()
        if hmac.compare_digest(_b64url_encode(expected), sig_seg):
            return payload
    return None


def _session():
    token = request.cookies.get("session_token")
    return verify_token(token) if token else None


def _current_user(session):
    """Full DB user for the session subject (may be None for a forged sub)."""
    return db.get_user(session.get("sub")) if session else None


# --- Public marketing -----------------------------------------------------

@bp.route("/", strict_slashes=False)
def index():
    return render_template("portal/landing.html", session=_session())


# --- Auth -----------------------------------------------------------------

@bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        user = db.authenticate(request.form.get("username", ""),
                               request.form.get("password", ""))  # safe check
        if user:
            resp = make_response(redirect(url_for("auth.dashboard")))
            resp.set_cookie("session_token", issue_token(user["username"], user["role"]),
                            httponly=True, samesite="Lax")
            return resp
        error = "Invalid username or password."
    return render_template("portal/login.html", error=error)


@bp.route("/logout")
def logout():
    resp = make_response(redirect(url_for("auth.login")))
    resp.delete_cookie("session_token")
    return resp


# --- Authenticated app ----------------------------------------------------

@bp.route("/dashboard")
def dashboard():
    session = _session()
    if not session:
        return redirect(url_for("auth.login"))
    user = _current_user(session) or {"full_name": session.get("sub"),
                                      "username": session.get("sub"),
                                      "company": "—", "plan": "—"}
    return render_template("portal/dashboard.html", session=session, user=user,
                           active="dashboard",
                           activity=db.activity_for(session.get("sub")),
                           invoices=db.invoices_for(session.get("sub")))


@bp.route("/billing")
def billing():
    session = _session()
    if not session:
        return redirect(url_for("auth.login"))
    user = _current_user(session) or {"plan": "—"}
    return render_template("portal/billing.html", session=session, user=user,
                           active="billing",
                           invoices=db.invoices_for(session.get("sub")))


@bp.route("/billing/invoice/<number>")
def invoice(number):
    session = _session()
    if not session:
        return redirect(url_for("auth.login"))
    # Scoped to the signed-in user (safe — not the vulnerable surface).
    inv = db.get_invoice(session.get("sub"), number)
    if inv is None:
        abort(404)
    user = _current_user(session) or {}
    return render_template("portal/invoice.html", session=session, user=user,
                           active="billing", invoice=inv)


PLANS = ["Starter", "Pro", "Enterprise"]


@bp.route("/billing/plan", methods=["POST"])
def change_plan():
    session = _session()
    if not session:
        return redirect(url_for("auth.login"))
    plan = request.form.get("plan", "")
    if plan in PLANS:
        db.update_plan(session.get("sub"), plan)
        flash(f"Your plan was changed to {plan}.", "success")
    else:
        flash("Please choose a valid plan.", "error")
    return redirect(url_for("auth.billing"))


@bp.route("/billing/card", methods=["POST"])
def update_card():
    session = _session()
    if not session:
        return redirect(url_for("auth.login"))
    number = request.form.get("number", "").replace(" ", "")
    if number.isdigit() and len(number) >= 12:
        flash(f"Card ending •••• {number[-4:]} saved. (Demo — no charge.)", "success")
    else:
        flash("Please enter a valid card number.", "error")
    return redirect(url_for("auth.billing"))


@bp.route("/billing/invoice/<number>/download")
def invoice_download(number):
    session = _session()
    if not session:
        return redirect(url_for("auth.login"))
    inv = db.get_invoice(session.get("sub"), number)
    if inv is None:
        abort(404)
    user = _current_user(session) or {}
    body = (
        "MERIDIAN, INC.\nbilling@meridian.example\n\n"
        f"Invoice:  {inv['number']}\n"
        f"Date:     {inv['date']}\n"
        f"Status:   {inv['status']}\n"
        f"Bill to:  {user.get('full_name','')} <{user.get('email','')}>\n\n"
        f"{user.get('plan','Subscription')} plan — monthly   ${inv['amount']:.2f}\n"
        "----------------------------------------\n"
        f"TOTAL                               ${inv['amount']:.2f}\n\n"
        "Demo environment — no real charge.\n"
    )
    return Response(
        body, mimetype="text/plain",
        headers={"Content-Disposition": f"attachment; filename={inv['number']}.txt"},
    )


@bp.route("/team")
def team():
    session = _session()
    if not session:
        return redirect(url_for("auth.login"))
    user = _current_user(session) or {"company": ""}
    return render_template("portal/team.html", session=session, user=user,
                           active="team", members=db.team_for(user.get("company", "")))


@bp.route("/team/invite", methods=["POST"])
def team_invite():
    session = _session()
    if not session:
        return redirect(url_for("auth.login"))
    user = _current_user(session) or {"company": ""}
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip()
    if name and "@" in email:
        db.add_team_member(user.get("company", ""), name, email, "Member")
        flash(f"Invitation sent to {email}.", "success")
    else:
        flash("Please provide a name and valid email.", "error")
    return redirect(url_for("auth.team"))


@bp.route("/settings")
def settings():
    session = _session()
    if not session:
        return redirect(url_for("auth.login"))
    user = _current_user(session) or {}
    return render_template("portal/settings.html", session=session, user=user,
                           active="settings")


@bp.route("/settings/profile", methods=["POST"])
def settings_profile():
    session = _session()
    if not session:
        return redirect(url_for("auth.login"))
    full_name = request.form.get("full_name", "").strip()
    email = request.form.get("email", "").strip()
    if full_name and "@" in email:
        db.update_profile(session.get("sub"), full_name, email)
        flash("Profile updated.", "success")
    else:
        flash("Please provide a name and valid email.", "error")
    return redirect(url_for("auth.settings"))


@bp.route("/settings/password", methods=["POST"])
def settings_password():
    session = _session()
    if not session:
        return redirect(url_for("auth.login"))
    current = request.form.get("current", "")
    new = request.form.get("new", "")
    if not db.authenticate(session.get("sub"), current):
        flash("Current password is incorrect.", "error")
    elif len(new) < 6:
        flash("New password must be at least 6 characters.", "error")
    else:
        db.update_password(session.get("sub"), new)
        flash("Password changed.", "success")
    return redirect(url_for("auth.settings"))


@bp.route("/settings/notifications", methods=["POST"])
def settings_notifications():
    session = _session()
    if not session:
        return redirect(url_for("auth.login"))
    flash("Notification preferences saved.", "success")
    return redirect(url_for("auth.settings"))


@bp.route("/support")
def support():
    session = _session()
    if not session:
        return redirect(url_for("auth.login"))
    return render_template("portal/support.html", session=session,
                           user=_current_user(session) or {}, active="support")


@bp.route("/admin")
def admin():
    session = _session()
    if not session:
        return redirect(url_for("auth.login"))
    if session.get("role") != "admin":
        return render_template("portal/forbidden.html", session=session,
                               user=_current_user(session) or {},
                               active="admin", role=session.get("role")), 403
    return render_template("portal/admin.html", session=session,
                           user=_current_user(session) or {"full_name": session.get("sub")},
                           active="admin", flag=AUTH_FLAG_A)
