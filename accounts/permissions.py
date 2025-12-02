from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAdminScindongo(BasePermission):
    """Accès réservé aux utilisateurs ayant le rôle ADMIN."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (
                user.is_superuser
                or user.is_staff
                or getattr(user, "is_admin_scindongo", False)
            )
        )


class IsCommercial(BasePermission):
    """Accès réservé aux utilisateurs COMMERCIAL."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (
                user.is_superuser
                or user.is_staff
                or getattr(user, "is_commercial", False)
            )
        )


class IsClient(BasePermission):
    """Accès réservé aux utilisateurs CLIENT."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (
                user.is_superuser
                or user.is_staff
                or getattr(user, "is_client", False)
            )
        )


class IsAdminOrCommercial(BasePermission):
    """
    Accès réservé :
    - superuser
    - staff
    - ADMIN SCINDONGO
    - COMMERCIAL
    """

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (
                user.is_superuser
                or user.is_staff
                or getattr(user, "is_admin_scindongo", False)
                or getattr(user, "is_commercial", False)
            )
        )
# ----- PATCH ÉTAPE 6 -----

class IsAdminScindongoOrDjangoAdmin(BasePermission):
    """
    Admin SCINDONGO ou admin Django (superuser / staff)
    """
    def has_permission(self, request, view):
        u = request.user
        return bool(
            u
            and u.is_authenticated
            and (
                getattr(u, "is_admin_scindongo", False)
                or u.is_superuser
                or u.is_staff
            )
        )


class IsAdminOrCommercialOrDjangoAdmin(BasePermission):
    """
    Admin SCINDONGO / Commercial / Admin Django
    """
    def has_permission(self, request, view):
        u = request.user
        return bool(
            u
            and u.is_authenticated
            and (
                getattr(u, "is_admin_scindongo", False)
                or getattr(u, "is_commercial", False)
                or u.is_superuser
                or u.is_staff
            )
        )
