from rest_framework.permissions import BasePermission


class IsRepartidor(BasePermission):
    message = "Esta cuenta no es una cuenta de repartidor"

    def has_permission(self, request, view):
        return bool(getattr(request.user, "es_repartidor", False))
