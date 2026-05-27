from abc import ABC, abstractmethod
from typing import Any

class ExchangeRatePort(ABC):
    @abstractmethod
    def get_usd_to_cop_rate(self) -> float:
        pass

class AllyServicePort(ABC):
    @abstractmethod
    def validate_user_trust(self, user_email: str) -> dict[str, Any]:
        pass
