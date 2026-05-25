from __future__ import annotations

from flask import Flask, jsonify
from werkzeug.exceptions import HTTPException

from ..errors import ApiError


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def handle_api_error(error: ApiError):
        payload = {
            "error": {
                "code": error.code,
                "message": error.message,
            }
        }
        if error.details:
            payload["error"]["details"] = error.details
        return jsonify(payload), error.status_code

    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        return (
            jsonify(
                {
                    "error": {
                        "code": str(error.name).lower().replace(" ", "_"),
                        "message": error.description,
                    }
                }
            ),
            int(error.code or 500),
        )

    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        app.logger.exception("Unexpected error", exc_info=error)
        return (
            jsonify(
                {
                    "error": {
                        "code": "internal_server_error",
                        "message": "Ocurrio un error interno en el servicio de pagos",
                    }
                }
            ),
            500,
        )
