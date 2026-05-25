from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
from werkzeug.security import check_password_hash, generate_password_hash

from .errors import ConflictError, NotFoundError, UnauthorizedError, ValidationError
from .repositories.auth_repository import SQLiteAuthRepository
from .settings import ACCESS_TOKEN_EXPIRES_MINUTES, JWT_ALGORITHM, JWT_SECRET, REFRESH_TOKEN_EXPIRES_DAYS


class AuthService:
    def __init__(self, *, repository: SQLiteAuthRepository) -> None:
        self.repository = repository

    def register(self, *, username: str, email: str, password: str):
        username = str(username or "").strip()
        email = str(email or "").strip().lower()
        password = str(password or "")

        if len(username) < 3:
            raise ValidationError("El username debe tener al menos 3 caracteres")
        if "@" not in email:
            raise ValidationError("El email no es valido")
        if len(password) < 6:
            raise ValidationError("La contrasena debe tener al menos 6 caracteres")

        if self.repository.get_user_by_username(username) is not None:
            raise ConflictError("El username ya existe")
        if self.repository.get_user_by_email(email) is not None:
            raise ConflictError("El email ya existe")

        user = self.repository.create_user(
            username=username,
            email=email,
            password_hash=generate_password_hash(password),
        )

        tokens = self._issue_tokens(user.id)
        return {"user": user.to_public_dict(), **tokens}

    def login(self, *, email: str, password: str):
        email = str(email or "").strip().lower()
        password = str(password or "")
        user = self.repository.get_user_by_email(email)
        if user is None or not check_password_hash(user.password_hash, password):
            raise UnauthorizedError("Credenciales invalidas")
        tokens = self._issue_tokens(user.id)
        return {"user": user.to_public_dict(), **tokens}

    def refresh(self, *, refresh_token: str):
        payload = self._decode_token(refresh_token, expected_type="refresh")
        user_id = int(payload["sub"])
        user = self.repository.get_user_by_id(user_id)
        if user is None:
            raise NotFoundError("Usuario no encontrado")
        tokens = self._issue_tokens(user.id)
        return {"user": user.to_public_dict(), **tokens}

    def me(self, *, access_token: str):
        payload = self._decode_token(access_token, expected_type="access")
        user_id = int(payload["sub"])
        user = self.repository.get_user_by_id(user_id)
        if user is None:
            raise NotFoundError("Usuario no encontrado")
        return user.to_public_dict()

    def reset_password(self, *, email: str, new_password: str):
        email = str(email or "").strip().lower()
        if len(str(new_password or "")) < 6:
            raise ValidationError("La contrasena debe tener al menos 6 caracteres")
        user = self.repository.get_user_by_email(email)
        if user is None:
            raise NotFoundError("Usuario no encontrado")
        raise ValidationError("Reset de password completo no implementado en esta version", code="not_implemented", status_code=501)

    def _issue_tokens(self, user_id: int) -> dict:
        now = datetime.now(timezone.utc)
        access_payload = {
            "sub": str(user_id),
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=ACCESS_TOKEN_EXPIRES_MINUTES)).timestamp()),
        }
        refresh_payload = {
            "sub": str(user_id),
            "type": "refresh",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(days=REFRESH_TOKEN_EXPIRES_DAYS)).timestamp()),
        }
        return {
            "access_token": jwt.encode(access_payload, JWT_SECRET, algorithm=JWT_ALGORITHM),
            "refresh_token": jwt.encode(refresh_payload, JWT_SECRET, algorithm=JWT_ALGORITHM),
            "token_type": "Bearer",
        }

    def _decode_token(self, token: str, *, expected_type: str) -> dict:
        if not token:
            raise UnauthorizedError("Token faltante")
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        except jwt.PyJWTError as exc:
            raise UnauthorizedError("Token invalido") from exc
        if payload.get("type") != expected_type:
            raise UnauthorizedError("Tipo de token invalido")
        return payload
