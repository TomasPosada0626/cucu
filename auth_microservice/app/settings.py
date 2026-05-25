from __future__ import annotations

import os

DATABASE_PATH = os.getenv("AUTH_DATABASE_PATH", "/app/data/auth.db")
JWT_SECRET = os.getenv("AUTH_JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRES_MINUTES = int(os.getenv("AUTH_ACCESS_TOKEN_MINUTES", "60"))
REFRESH_TOKEN_EXPIRES_DAYS = int(os.getenv("AUTH_REFRESH_TOKEN_DAYS", "7"))
