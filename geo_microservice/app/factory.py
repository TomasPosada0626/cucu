from __future__ import annotations

from flask import Flask

from .api.errors import register_error_handlers
from .logging_utils import configure_structured_logging
from .api.routes import geo_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False
    configure_structured_logging(app)

    app.register_blueprint(geo_bp)
    register_error_handlers(app)

    return app
