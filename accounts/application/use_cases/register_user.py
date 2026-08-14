from __future__ import annotations

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError

from common.exceptions import ConflictError, ValidationError

from ...domain.repositories import UserRepository
from ...domain.services import AccountPolicyService
from ..dto import UserDTO


class RegisterUserUseCase:
    def __init__(
        self,
        *,
        user_repository: UserRepository,
        policy_service: AccountPolicyService | None = None,
        password_validator=validate_password,
    ):
        self._user_repository = user_repository
        self._policy_service = policy_service or AccountPolicyService()
        self._password_validator = password_validator

    def execute(self, *, nombre: str, email: str, password: str, es_repartidor: bool = False) -> UserDTO:
        normalized_name = self._policy_service.normalize_name(nombre)
        normalized_email = self._policy_service.normalize_email(email)
        try:
            self._password_validator(password)
        except DjangoValidationError as exc:
            raise ValidationError(" ".join(exc.messages)) from exc

        if self._user_repository.exists_by_email(normalized_email):
            raise ConflictError("El email ya está registrado")

        try:
            user = self._user_repository.create_user(
                nombre=normalized_name,
                email=normalized_email,
                password=password,
                es_repartidor=es_repartidor,
            )
        except IntegrityError as exc:
            raise ConflictError("El email ya está registrado") from exc

        return UserDTO.from_model(user)
