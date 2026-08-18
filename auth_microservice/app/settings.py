from __future__ import annotations

import os

POSTGRES_DSN = os.getenv(
    "AUTH_POSTGRES_DSN",
    "postgresql://{user}:{password}@{host}:{port}/{db}".format(
        user=os.getenv("POSTGRES_USER", "cucu"),
        password=os.getenv("POSTGRES_PASSWORD", ""),
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        db=os.getenv("POSTGRES_DB", "cucu"),
    ),
)
POSTGRES_SCHEMA = os.getenv("AUTH_POSTGRES_SCHEMA", "auth_service")
JWT_SECRET = os.getenv("AUTH_JWT_SECRET", "change-me-in-production")
JWT_ALGORITHM = "HS256"
# Antes leia AUTH_ACCESS_TOKEN_MINUTES/AUTH_REFRESH_TOKEN_DAYS, pero
# docker-compose.yml, el Dockerfile y .env.example siempre seteaban
# AUTH_ACCESS_TOKEN_TTL_MINUTES/AUTH_REFRESH_TOKEN_TTL_DAYS (con "_TTL_") -
# mismo tipo de bug que GOOGLE_MAPS_API_KEY: la variable nunca llegaba y el
# servicio corria siempre con los defaults hardcodeados, sin error visible.
ACCESS_TOKEN_EXPIRES_MINUTES = int(os.getenv("AUTH_ACCESS_TOKEN_TTL_MINUTES", "60"))
REFRESH_TOKEN_EXPIRES_DAYS = int(os.getenv("AUTH_REFRESH_TOKEN_TTL_DAYS", "7"))
