from rest_framework.permissions import BasePermission


class IsOwnerOrAdmin(BasePermission):

    def has_object_permission(
        self,
        request,
        view,
        obj
    ):
        if request.user.role == "ADMIN":
            return True

        return obj.citizen == request.user
    
    