from __future__ import annotations

from dataclasses import dataclass


@dataclass
class User:
    id: int
    username: str
    email: str
    password_hash: str
    is_active: bool

    def to_public_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "is_active": self.is_active,
        }
