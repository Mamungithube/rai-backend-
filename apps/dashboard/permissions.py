from rest_framework import permissions


class IsAppAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (getattr(request.user, 'is_admin', False) or getattr(request.user, 'is_superuser', False) or getattr(request.user, 'is_staff', False))
        )

