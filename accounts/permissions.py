from rest_framework.permissions import BasePermission, SAFE_METHODS

from .utils import is_admin_user


class IsAdminScindongo(BasePermission):
    """Accès réservé aux utilisateurs ayant le rôle ADMIN."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and is_admin_user(user))


class IsCommercial(BasePermission):
    """Accès réservé aux utilisateurs COMMERCIAL."""

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (
                getattr(user, "is_commercial", False)
                or is_admin_user(user)
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
                getattr(user, "is_client", False)
                or is_admin_user(user)
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
                is_admin_user(user)
                or getattr(user, "is_commercial", False)
            )
        )


class IsAdminScindongoOrDjangoAdmin(BasePermission):
    """
    Admin SCINDONGO ou admin Django (superuser / staff)
    """
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and is_admin_user(u))


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
                is_admin_user(u)
                or getattr(u, "is_commercial", False)
            )
        )


class IsClientOwnerOrAdminOrCommercial(BasePermission):
    """
    Propriétaire du Client, ou Admin, ou Commercial.
    Utilisé pour les endpoints liés au client (réservations, paiements, etc.)
    """
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        # Admin/Commercial ont accès à tout
        if is_admin_user(request.user) or getattr(request.user, "is_commercial", False):
            return True
        
        # Client doit être le propriétaire
        client_profile = getattr(request.user, "client_profile", None)
        if client_profile and obj.client == client_profile:
            return True
        
        return False


class IsReservationOwnerOrAdminOrCommercial(BasePermission):
    """
    Propriétaire de la réservation (via client_profile), ou Admin, ou Commercial.
    """
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        # obj est une Reservation
        # Admin/Commercial ont accès
        if is_admin_user(request.user) or getattr(request.user, "is_commercial", False):
            return True
        
        # Client : doit être le client de la réservation
        client_profile = getattr(request.user, "client_profile", None)
        if client_profile and obj.client == client_profile:
            return True
        
        return False

