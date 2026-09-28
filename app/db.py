"""SQLite data layer: schema, seed data, and query helpers.

The database is a single file, seeded idempotently on startup. On ephemeral
hosting the file is recreated every deploy/restart, giving each run a clean,
identical, known-good state — ideal for a fair contest.

Design note: every helper here that takes user input uses **parameterized**
queries and is safe. The single intentional SQL-injection vulnerability lives
in the store search (see `app/challenges/sqli.py`), where the query is built by
string concatenation on purpose.
"""
import os
import random
import sqlite3
from datetime import datetime, timezone

from werkzeug.security import generate_password_hash, check_password_hash

from .config import Config

DB_PATH = Config.DB_PATH


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS categories (
    id    INTEGER PRIMARY KEY,
    name  TEXT NOT NULL,
    slug  TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS products (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    description TEXT NOT NULL,
    price       REAL NOT NULL,
    category    TEXT NOT NULL,
    stock       INTEGER NOT NULL DEFAULT 0,
    rating      REAL NOT NULL DEFAULT 0,
    emoji       TEXT NOT NULL DEFAULT '📦'
);

-- The Q1 flag hides in a table the store UI never queries directly.
CREATE TABLE IF NOT EXISTS internal_flags (
    id          INTEGER PRIMARY KEY,
    flag_value  TEXT NOT NULL,
    note        TEXT NOT NULL
);

-- Q2 (Meridian) accounts. Passwords are stored hashed.
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL DEFAULT 'member',
    full_name     TEXT NOT NULL,
    email         TEXT NOT NULL DEFAULT '',
    company       TEXT NOT NULL DEFAULT '',
    plan          TEXT NOT NULL DEFAULT 'Starter'
);

CREATE TABLE IF NOT EXISTS invoices (
    id       INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    number   TEXT NOT NULL,
    date     TEXT NOT NULL,
    amount   REAL NOT NULL,
    status   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS activity_log (
    id       INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    when_at  TEXT NOT NULL,
    text     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS team_members (
    id      INTEGER PRIMARY KEY,
    company TEXT NOT NULL,
    name    TEXT NOT NULL,
    email   TEXT NOT NULL,
    role    TEXT NOT NULL
);

-- Q3 (DataBridge API) accounts. `api_token` authenticates the owner.
CREATE TABLE IF NOT EXISTS api_accounts (
    id           INTEGER PRIMARY KEY,
    owner_name   TEXT NOT NULL,
    email        TEXT NOT NULL,
    plan         TEXT NOT NULL,
    api_token    TEXT NOT NULL UNIQUE,
    private_note TEXT NOT NULL
);

-- Voltix commerce: product reviews (P1), orders, and decoy form captures.
CREATE TABLE IF NOT EXISTS reviews (
    id         INTEGER PRIMARY KEY,
    product_id INTEGER NOT NULL,
    author     TEXT NOT NULL,
    rating     INTEGER NOT NULL,
    body       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orders (
    id           INTEGER PRIMARY KEY,
    order_number TEXT NOT NULL UNIQUE,
    email        TEXT NOT NULL,
    full_name    TEXT NOT NULL,
    address      TEXT NOT NULL,
    city         TEXT NOT NULL,
    postcode     TEXT NOT NULL,
    subtotal     REAL NOT NULL,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS order_items (
    id           INTEGER PRIMARY KEY,
    order_number TEXT NOT NULL,
    product_id   INTEGER NOT NULL,
    name         TEXT NOT NULL,
    price        REAL NOT NULL,
    qty          INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS newsletter_subscribers (
    id         INTEGER PRIMARY KEY,
    email      TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contact_messages (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    email      TEXT NOT NULL,
    message    TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""

CATEGORIES = [
    ("Peripherals", "peripherals"),
    ("Audio", "audio"),
    ("Displays", "displays"),
    ("Storage", "storage"),
    ("Accessories", "accessories"),
]

# (name, description, price, category, stock, rating, emoji)
PRODUCTS = [
    ("Wireless Mouse", "Ergonomic 2.4GHz mouse with silent clicks and a 12-month battery.", 24.99, "Peripherals", 143, 4.5, "🖱️"),
    ("Mechanical Keyboard", "Hot-swappable switches, per-key RGB, aluminium frame.", 89.00, "Peripherals", 61, 4.8, "⌨️"),
    ("Ergonomic Trackball", "Thumb-operated trackball for all-day comfort.", 54.50, "Peripherals", 27, 4.2, "🖱️"),
    ("Noise-cancelling Headphones", "Over-ear ANC headphones, 30h battery, USB-C.", 129.00, "Audio", 38, 4.7, "🎧"),
    ("Desk Speakers", "Compact stereo speakers with rich bass.", 64.00, "Audio", 52, 4.1, "🔊"),
    ("USB Microphone", "Cardioid condenser mic for calls and streaming.", 78.00, "Audio", 44, 4.4, "🎙️"),
    ("27\" 4K Monitor", "27-inch IPS 4K display, 99% sRGB, USB-C 65W.", 329.00, "Displays", 19, 4.6, "🖥️"),
    ("Portable Monitor", "15.6-inch 1080p USB-C travel display.", 179.00, "Displays", 23, 4.3, "🖥️"),
    ("Monitor Light Bar", "Screen-mounted LED bar, auto-dimming.", 55.00, "Displays", 71, 4.5, "💡"),
    ("1TB NVMe SSD", "PCIe Gen4 drive, up to 7000MB/s reads.", 99.99, "Storage", 88, 4.9, "💾"),
    ("Portable SSD 2TB", "Pocket USB-C SSD, IP55 dust/water resistant.", 149.00, "Storage", 34, 4.7, "💾"),
    ("SD Card 256GB", "UHS-II card for cameras, 300MB/s.", 42.00, "Storage", 120, 4.4, "💳"),
    ("USB-C Hub", "7-in-1 hub: HDMI, card reader, 3×USB-A, PD.", 39.50, "Accessories", 96, 4.2, "🔌"),
    ("Laptop Stand", "Aluminium adjustable stand, folds flat.", 34.00, "Accessories", 63, 4.5, "📐"),
    ("Cable Organizer Kit", "Magnetic clips and sleeves for tidy desks.", 18.00, "Accessories", 210, 4.0, "🧷"),
    ("Webcam 1080p", "Full-HD webcam with privacy shutter.", 45.99, "Accessories", 57, 4.1, "📷"),
]

# Set A flag for the SQL injection challenge.
SQLI_FLAG_A = "FLAG{scaler_un10n_sql1_r3c0n_a1}"

# Q2 (Meridian) accounts. The member credential is handed to students in the
# challenge prompt; the admin password is strong and unknown (the intended path
# is a JWT forgery, not cracking the admin login).
USERS = [
    # (username, password, role, full_name, email, company, plan)
    ("alice", "member2026", "member", "Alice Turner",
     "alice@northwind.example", "Northwind Traders", "Pro"),
    ("bob", "hunter2meh", "member", "Bob Nadal",
     "bob@northwind.example", "Northwind Traders", "Pro"),
    ("admin", "S7r0ng-Adm1n-Pw-982473-do-not-share", "admin",
     "Site Administrator", "admin@meridian.example", "Meridian", "Enterprise"),
]

MERIDIAN_INVOICES = [
    # (username, number, date, amount, status)
    ("alice", "INV-2026-0412", "2026-09-01", 149.00, "Paid"),
    ("alice", "INV-2026-0388", "2026-08-01", 149.00, "Paid"),
    ("alice", "INV-2026-0355", "2026-07-01", 149.00, "Paid"),
    ("alice", "INV-2026-0431", "2026-10-01", 149.00, "Due"),
    ("bob", "INV-2026-0410", "2026-09-01", 149.00, "Paid"),
]

MERIDIAN_ACTIVITY = [
    # (username, when_at, text)
    ("alice", "2026-09-24 14:32", "Signed in from Chrome on macOS"),
    ("alice", "2026-09-22 09:11", "Exported the September usage report"),
    ("alice", "2026-09-20 16:45", "Invited a new team member"),
    ("alice", "2026-09-18 11:02", "Updated billing details"),
    ("bob", "2026-09-23 10:05", "Signed in from Firefox on Windows"),
]

MERIDIAN_TEAM = [
    # (company, name, email, role)
    ("Northwind Traders", "Alice Turner", "alice@northwind.example", "Owner"),
    ("Northwind Traders", "Bob Nadal", "bob@northwind.example", "Member"),
    ("Northwind Traders", "Chidi Okafor", "chidi@northwind.example", "Member"),
    ("Northwind Traders", "Dana Ruiz", "dana@northwind.example", "Billing"),
]

# Q3 (DataBridge API) accounts. The student is given the token for account 1007.
# The flag lives in the system account (1000) — reachable only via BOLA (reading
# an account that isn't yours). Ids are non-contiguous to require real probing.
API_FLAG_A = "FLAG{scaler_b0la_id_3num_ap1_a3}"
API_ACCOUNTS = [
    # (id, owner_name, email, plan, api_token, private_note)
    (1000, "DataBridge System", "system@databridge.example", "internal",
     "db_live_sk_SYSTEM_0e91c4", API_FLAG_A),
    (1004, "Nina Patel", "nina@vaultworks.example", "pro",
     "db_live_sk_nina_2a71b9", "Renewal due in March."),
    (1007, "You (Demo User)", "demo@databridge.example", "starter",
     "db_live_sk_demo_7c3f9a2b1e", "Welcome to DataBridge!"),
    (1012, "Marco Reyes", "marco@northwind.example", "pro",
     "db_live_sk_marco_5f0c8d", "Migrating from legacy CRM."),
    (1015, "Aiko Tanaka", "aiko@lumen.example", "enterprise",
     "db_live_sk_aiko_9b347e", "Quarterly export automated."),
]


# A few reviews so product pages feel real (P1 content, safe data).
REVIEWS = [
    (2, "Devon R.", 5, "Best keyboard I've owned. The switches feel amazing."),
    (2, "Priya S.", 4, "Great typing experience, RGB is a nice bonus."),
    (1, "Chen L.", 5, "Silent and precise. Battery lasts forever."),
    (4, "Marcus T.", 5, "Noise cancelling is superb on flights."),
    (7, "Ana V.", 4, "Gorgeous 4K panel; stand could be sturdier."),
    (10, "Sam K.", 5, "Blazing fast drive, easy install."),
]


def seed(conn):
    cur = conn.cursor()

    if cur.execute("SELECT COUNT(*) c FROM categories").fetchone()["c"] == 0:
        cur.executemany(
            "INSERT INTO categories (name, slug) VALUES (?, ?)", CATEGORIES
        )

    if cur.execute("SELECT COUNT(*) c FROM products").fetchone()["c"] == 0:
        cur.executemany(
            "INSERT INTO products (name, description, price, category, stock, rating, emoji) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            PRODUCTS,
        )

    if cur.execute("SELECT COUNT(*) c FROM internal_flags").fetchone()["c"] == 0:
        cur.execute(
            "INSERT INTO internal_flags (flag_value, note) VALUES (?, ?)",
            (SQLI_FLAG_A, "Reachable only by reading across tables."),
        )

    if cur.execute("SELECT COUNT(*) c FROM users").fetchone()["c"] == 0:
        cur.executemany(
            "INSERT INTO users (username, password_hash, role, full_name, email, company, plan) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(u, generate_password_hash(p), r, n, e, co, pl)
             for (u, p, r, n, e, co, pl) in USERS],
        )

    if cur.execute("SELECT COUNT(*) c FROM invoices").fetchone()["c"] == 0:
        cur.executemany(
            "INSERT INTO invoices (username, number, date, amount, status) VALUES (?, ?, ?, ?, ?)",
            MERIDIAN_INVOICES,
        )

    if cur.execute("SELECT COUNT(*) c FROM activity_log").fetchone()["c"] == 0:
        cur.executemany(
            "INSERT INTO activity_log (username, when_at, text) VALUES (?, ?, ?)",
            MERIDIAN_ACTIVITY,
        )

    if cur.execute("SELECT COUNT(*) c FROM team_members").fetchone()["c"] == 0:
        cur.executemany(
            "INSERT INTO team_members (company, name, email, role) VALUES (?, ?, ?, ?)",
            MERIDIAN_TEAM,
        )

    if cur.execute("SELECT COUNT(*) c FROM api_accounts").fetchone()["c"] == 0:
        cur.executemany(
            "INSERT INTO api_accounts (id, owner_name, email, plan, api_token, private_note) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            API_ACCOUNTS,
        )

    if cur.execute("SELECT COUNT(*) c FROM reviews").fetchone()["c"] == 0:
        cur.executemany(
            "INSERT INTO reviews (product_id, author, rating, body) VALUES (?, ?, ?, ?)",
            REVIEWS,
        )

    conn.commit()


# If an existing DB predates the current schema (e.g. a stale contest.db), it is
# rebuilt from scratch. The data here is disposable seed data, so this is safe
# and prevents "no such column" 500s after a schema change.
_EXPECTED_COLUMNS = {
    "users": {"email", "company", "plan"},
    "api_accounts": {"private_note"},
}


def _schema_is_current(conn):
    for table, needed in _EXPECTED_COLUMNS.items():
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
        if rows and not needed.issubset({r[1] for r in rows}):
            return False
    return True


def init_db():
    conn = get_db()
    conn.executescript(SCHEMA)
    if not _schema_is_current(conn):
        conn.close()
        if DB_PATH != ":memory:" and os.path.exists(DB_PATH):
            os.remove(DB_PATH)
        conn = get_db()
        conn.executescript(SCHEMA)
    seed(conn)
    conn.close()


# --- Safe query helpers (parameterized) -----------------------------------

def list_categories():
    conn = get_db()
    rows = conn.execute("SELECT name, slug FROM categories ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def featured_products(limit=8):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM products ORDER BY rating DESC, id ASC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def products_in_category(slug, limit=50):
    conn = get_db()
    row = conn.execute("SELECT name FROM categories WHERE slug = ?", (slug,)).fetchone()
    if row is None:
        conn.close()
        return None, []
    name = row["name"]
    rows = conn.execute(
        "SELECT * FROM products WHERE category = ? ORDER BY id LIMIT ?", (name, limit)
    ).fetchall()
    conn.close()
    return name, [dict(r) for r in rows]


def get_product(pid):
    conn = get_db()
    row = conn.execute("SELECT * FROM products WHERE id = ?", (pid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def related_products(category, exclude_id, limit=4):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM products WHERE category = ? AND id != ? ORDER BY rating DESC LIMIT ?",
        (category, exclude_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# Columns the vulnerable search selects, rendered as product cards (7 columns).
SEARCH_COLUMNS = "id, name, description, price, category, emoji, rating"


def search_products(q):
    """INTENTIONALLY VULNERABLE product search (string-concatenated SQL).

    No ORDER BY / LIMIT in the SQL — sorting and pagination happen in Python — so
    a `-- ` comment in a payload cleanly terminates the statement. Returns
    (rows, error). This is the single injection point in Voltix.
    """
    query = (
        f"SELECT {SEARCH_COLUMNS} FROM products "
        f"WHERE name LIKE '%{q}%'"
    )
    conn = get_db()
    try:
        rows = [dict(r) for r in conn.execute(query).fetchall()]
        return rows, None
    except Exception as e:
        return None, str(e)
    finally:
        conn.close()


def category_products(slug):
    """SAFE (parameterized) — all products in a category, unsorted."""
    conn = get_db()
    cat = conn.execute("SELECT name FROM categories WHERE slug = ?", (slug,)).fetchone()
    if cat is None:
        conn.close()
        return None, []
    rows = conn.execute(
        "SELECT * FROM products WHERE category = ?", (cat["name"],)
    ).fetchall()
    conn.close()
    return cat["name"], [dict(r) for r in rows]


def products_by_ids(ids):
    """SAFE — fetch products for a set of ids (for the cart)."""
    if not ids:
        return []
    conn = get_db()
    marks = ",".join("?" for _ in ids)
    rows = conn.execute(
        f"SELECT * FROM products WHERE id IN ({marks})", tuple(ids)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def reviews_for(product_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT author, rating, body FROM reviews WHERE product_id = ? ORDER BY id DESC",
        (product_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def create_order(email, full_name, address, city, postcode, items, subtotal):
    """Create an order + its line items. `items` = list of dicts with
    id/name/price/qty. Returns the generated order number."""
    number = "VLT-" + "".join(str(random.randint(0, 9)) for _ in range(8))
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = get_db()
    conn.execute(
        "INSERT INTO orders (order_number, email, full_name, address, city, postcode, subtotal, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (number, email, full_name, address, city, postcode, subtotal, now),
    )
    conn.executemany(
        "INSERT INTO order_items (order_number, product_id, name, price, qty) VALUES (?, ?, ?, ?, ?)",
        [(number, it["id"], it["name"], it["price"], it["qty"]) for it in items],
    )
    conn.commit()
    conn.close()
    return number


def get_order(number):
    conn = get_db()
    order = conn.execute(
        "SELECT * FROM orders WHERE order_number = ?", (number,)
    ).fetchone()
    if order is None:
        conn.close()
        return None, []
    items = conn.execute(
        "SELECT * FROM order_items WHERE order_number = ?", (number,)
    ).fetchall()
    conn.close()
    return dict(order), [dict(i) for i in items]


def add_newsletter(email):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = get_db()
    conn.execute("INSERT INTO newsletter_subscribers (email, created_at) VALUES (?, ?)",
                 (email, now))
    conn.commit()
    conn.close()


def add_contact_message(name, email, message):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn = get_db()
    conn.execute("INSERT INTO contact_messages (name, email, message, created_at) VALUES (?, ?, ?, ?)",
                 (name, email, message, now))
    conn.commit()
    conn.close()


# --- Q2 auth helpers (parameterized; password check is constant-time) ------

def authenticate(username, password):
    """Return the user dict if credentials are valid, else None."""
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    if row and check_password_hash(row["password_hash"], password):
        return dict(row)
    return None


def get_user(username):
    conn = get_db()
    row = conn.execute(
        "SELECT id, username, role, full_name, email, company, plan "
        "FROM users WHERE username = ?",
        (username,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def invoices_for(username):
    conn = get_db()
    rows = conn.execute(
        "SELECT number, date, amount, status FROM invoices WHERE username = ? "
        "ORDER BY date DESC",
        (username,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_invoice(username, number):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM invoices WHERE username = ? AND number = ?",
        (username, number),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def activity_for(username, limit=6):
    conn = get_db()
    rows = conn.execute(
        "SELECT when_at, text FROM activity_log WHERE username = ? "
        "ORDER BY when_at DESC LIMIT ?",
        (username, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def team_for(company):
    conn = get_db()
    rows = conn.execute(
        "SELECT name, email, role FROM team_members WHERE company = ? ORDER BY id",
        (company,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_profile(username, full_name, email):
    conn = get_db()
    conn.execute(
        "UPDATE users SET full_name = ?, email = ? WHERE username = ?",
        (full_name, email, username),
    )
    conn.commit()
    conn.close()


def update_password(username, new_password):
    conn = get_db()
    conn.execute(
        "UPDATE users SET password_hash = ? WHERE username = ?",
        (generate_password_hash(new_password), username),
    )
    conn.commit()
    conn.close()


def update_plan(username, plan):
    conn = get_db()
    conn.execute("UPDATE users SET plan = ? WHERE username = ?", (plan, username))
    conn.commit()
    conn.close()


def add_team_member(company, name, email, role="Member"):
    conn = get_db()
    conn.execute(
        "INSERT INTO team_members (company, name, email, role) VALUES (?, ?, ?, ?)",
        (company, name, email, role),
    )
    conn.commit()
    conn.close()


# --- Q3 API helpers (parameterized) ---------------------------------------

def api_account_by_token(token):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM api_accounts WHERE api_token = ?", (token,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def api_account_by_id(account_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM api_accounts WHERE id = ?", (account_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None
