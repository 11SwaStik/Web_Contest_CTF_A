"""Q3 — API Attacks (Set A): the DataBridge developer platform.

A small but real-feeling API product: a marketing landing page, a developer
reference, and a JSON API secured with bearer tokens. Authentication works
correctly (a valid token is required), but the account endpoint has **Broken
Object Level Authorization (BOLA / IDOR)**: it verifies the caller is
authenticated but NOT that the requested account belongs to them. Any valid
token can read any account by changing the id — including the internal `system`
account (1000), whose private note holds the flag.

Intended path:
  1. Land on /api, explore to the reference and the sandbox key.
  2. Call GET /api/v1/accounts/me — see your own account (id 1007).
  3. Change the id to read accounts that aren't yours; enumerate to 1000.
  4. The system account's `private_note` is the flag.

Intentionally vulnerable code for an authorised training contest — do not add
the missing ownership check.
"""
from flask import Blueprint, request, jsonify, render_template

from .. import db

bp = Blueprint("api", __name__, url_prefix="/api")

# The sandbox key is shown to developers in the reference (like a real test key).
DEMO_TOKEN = "db_live_sk_demo_7c3f9a2b1e"
DEMO_ACCOUNT_ID = 1007


def _bearer_token():
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[len("Bearer "):].strip()
    return None


def _authenticate():
    """Return the calling account for a valid token, else None."""
    token = _bearer_token()
    if not token:
        return None
    return db.api_account_by_token(token)


def _unauthorized():
    return jsonify(
        error="unauthorized",
        message="Provide a valid 'Authorization: Bearer <token>' header.",
    ), 401


def _public_view(account):
    return {
        "id": account["id"],
        "owner_name": account["owner_name"],
        "email": account["email"],
        "plan": account["plan"],
        "private_note": account["private_note"],
    }


# --- Pages ---------------------------------------------------------------

@bp.route("/", strict_slashes=False)
def landing():
    return render_template("api/landing.html")


@bp.route("/docs")
def docs():
    return render_template("api/docs.html", token=DEMO_TOKEN,
                           account_id=DEMO_ACCOUNT_ID)


def _events_for(account):
    """Synthetic, caller-scoped event feed (benign decoy)."""
    seed = [
        ("account.updated", "Account profile updated"),
        ("invoice.paid", "Invoice INV-2026-0412 marked paid"),
        ("key.used", "API key used from 10.14.22.6"),
        ("usage.threshold", "Reached 68% of monthly request quota"),
        ("member.invited", "Team member invited"),
    ]
    out = []
    for i, (etype, msg) in enumerate(seed):
        out.append({
            "id": f"evt_{account['id']}{1000 + i}",
            "type": etype,
            "message": msg,
            "created": f"2026-09-{24 - i:02d}T10:0{i}:00Z",
        })
    return out


@bp.route("/dashboard")
def dashboard():
    # Sandbox dashboard: shows the demo account, its key, usage and events.
    account = db.api_account_by_id(DEMO_ACCOUNT_ID)
    used, limit = 68420, 100000
    return render_template("api/dashboard.html", account=account,
                           token=DEMO_TOKEN, used=used, limit=limit,
                           pct=round(used * 100 / limit),
                           events=_events_for(account))


# --- JSON API ------------------------------------------------------------

@bp.route("/v1/accounts/me")
def me():
    caller = _authenticate()
    if not caller:
        return _unauthorized()
    return jsonify(_public_view(caller))


@bp.route("/v1/accounts/<int:account_id>")
def get_account(account_id):
    caller = _authenticate()
    if not caller:
        return _unauthorized()

    # --- BOLA: authenticated, but NO ownership check on account_id. ---
    account = db.api_account_by_id(account_id)
    if not account:
        return jsonify(error="not_found",
                       message=f"No account with id {account_id}."), 404
    return jsonify(_public_view(account))


@bp.route("/v1/usage")
def usage():
    # Decoy: benign, correctly scoped to the caller. No flag here.
    caller = _authenticate()
    if not caller:
        return _unauthorized()
    limits = {"starter": 10000, "pro": 100000,
              "enterprise": 1000000, "internal": 0}
    return jsonify(
        account_id=caller["id"],
        plan=caller["plan"],
        requests_this_month=4213 if caller["id"] == DEMO_ACCOUNT_ID else 0,
        monthly_limit=limits.get(caller["plan"], 10000),
    )


@bp.route("/v1/events")
def events():
    # Decoy: benign, correctly scoped to the caller (list envelope). No flag.
    caller = _authenticate()
    if not caller:
        return _unauthorized()
    return jsonify(object="list", data=_events_for(caller), has_more=False)


@bp.route("/v1/health")
def health():
    # Public status endpoint.
    return jsonify(status="operational", version="v1")
