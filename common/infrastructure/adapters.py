import os
import httpx
from typing import Any
from ..domain.ports import ExchangeRatePort, AllyServicePort

class ThirdPartyExchangeRateAdapter(ExchangeRatePort):
    def get_usd_to_cop_rate(self) -> float:
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get("https://api.exchangerate-api.com/v4/latest/USD")
                response.raise_for_status()
                data = response.json()
                return data.get("rates", {}).get("COP", 4000.0)
        except Exception:
            # TODO: Logging could be added here
            return 4000.0


class HttpAllyServiceAdapter(AllyServicePort):
    def __init__(self):
        self.base_url = os.environ.get("ALLY_SERVICE_URL", "").rstrip("/")

    def validate_user_trust(self, user_email: str) -> dict[str, Any]:
        # Fallback/Mock documentado como lo pide el Entregable 2
        if not self.base_url:
            return {
                "status": "verified",
                "score": 85,
                "email": user_email,
                "mocked": True,
                "message": "Fallback applied. Configure ALLY_SERVICE_URL to connect to real service."
            }

        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.post(f"{self.base_url}/api/validate", json={"email": user_email})
                response.raise_for_status()
                return response.json()
        except Exception as e:
            return {
                "status": "unknown",
                "score": 0,
                "email": user_email,
                "mocked": False,
                "error": str(e)
            }
