import logging

from flask import Flask, render_template, session

from .config import Config
from .db import init_db
from .challenges.sqli import bp as shop_bp
from .challenges.auth import bp as auth_bp
from .challenges.api import bp as api_bp


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Seed SQLite on startup (idempotent; safe on every boot).
    init_db()

    _register_template_helpers(app)

    @app.context_processor
    def inject_cart_count():
        try:
            count = sum(int(v) for v in session.get("cart", {}).values())
        except (ValueError, TypeError):
            count = 0
        return {"cart_count": count}

    app.register_blueprint(shop_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(api_bp)

    @app.route("/")
    def index():
        # Scaler-branded engagement briefing (the "wrapper"). Lists the in-scope
        # targets by brand name only — no vulnerability hints. The instructor can
        # share this page, or hand out the target links directly.
        targets = [
            {"name": "Voltix", "kind": "E-commerce", "url": "/shop",
             "desc": "Consumer electronics storefront.",
             "icon": "bag", "accent": "#4f46e5"},
            {"name": "Meridian", "kind": "SaaS portal", "url": "/portal",
             "desc": "Business customer account portal.",
             "icon": "layout", "accent": "#0d9488"},
            {"name": "DataBridge", "kind": "Developer API", "url": "/api",
             "desc": "REST API and developer platform.",
             "icon": "code", "accent": "#7c3aed"},
        ]
        return render_template("contest/briefing.html", targets=targets)

    @app.route("/healthz")
    def healthz():
        return {"status": "ok"}

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(_e):
        app.logger.exception("Unhandled server error")
        return render_template("errors/500.html"), 500

    return app


def _register_template_helpers(app):
    @app.template_filter("money")
    def money(value):
        try:
            return f"${float(value):,.2f}"
        except (TypeError, ValueError):
            return value

    @app.template_filter("stars")
    def stars(value):
        try:
            n = int(round(float(value)))
        except (TypeError, ValueError):
            return ""
        n = max(0, min(5, n))
        return "★" * n + "☆" * (5 - n)
