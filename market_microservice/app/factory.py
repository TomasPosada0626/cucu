from __future__ import annotations

import os

from flask import Flask

from .api.errors import register_error_handlers
from .api.routes import market_bp
from .repositories.market_repository import SQLiteMarketRepository
from .services import MarketService


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["JSON_SORT_KEYS"] = False

    database_path = os.getenv("MARKET_DATABASE_PATH", "/app/data/market.db")

    repository = SQLiteMarketRepository(database_path)
    repository.initialize()

    app.config["market_service"] = MarketService(repository=repository)

    app.register_blueprint(market_bp)
    register_error_handlers(app)

    return app
