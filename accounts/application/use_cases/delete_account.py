from __future__ import annotations

from common.exceptions import ConflictError, ValidationError

from ...domain.repositories import UserRepository


class DeleteAccountUseCase:
    def __init__(self, *, user_repository: UserRepository):
        self._user_repository = user_repository

    def execute(self, *, user, password: str) -> None:
        if not password:
            raise ValidationError("Debes ingresar tu contraseña para eliminar la cuenta")
        if not user.check_password(password):
            # ValidationError (400), no AuthenticationError (401): un 401 en este
            # endpoint autenticado dispara el refresh-and-retry de authenticatedFetch
            # en el frontend, que termina deslogueando al usuario en vez de mostrarle
            # el error de contraseña incorrecta.
            raise ValidationError("Contraseña incorrecta")

        blocker = self._user_repository.find_deletion_blocker(user=user)
        if blocker:
            raise ConflictError(blocker)

        self._user_repository.delete_user(user=user)
