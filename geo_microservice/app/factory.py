from __future__ import annotations

from flask import Flask

from .api.errors import register_error_handlers
from .api.routes import geo_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    app.register_blueprint(geo_bp)
    register_error_handlers(app)

    return app
