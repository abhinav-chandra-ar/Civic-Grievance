from rest_framework.permissions import BasePermission

_OFFICER_ROLES = {"JUNIOR_OFFICER", "SENIOR_OFFICER", "ADMIN"}
_SENIOR_ROLES = {"SENIOR_OFFICER", "ADMIN"}


class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        if not (request.user and request.user.is_authenticated):
            return False
        if request.user.role == "ADMIN":
            return True
        return obj.citizen == request.user


class IsOfficer(BasePermission):
    """Junior Officer, Senior Officer, or Admin."""
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in _OFFICER_ROLES
        )


class IsSeniorOfficerOrAdmin(BasePermission):
    """Senior Officer or Admin only."""
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in _SENIOR_ROLES
        )
