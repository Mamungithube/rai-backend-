from rest_framework import permissions
from .models import Membership


class IsCommunityAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return Membership.objects.filter(
            community=obj,
            user=request.user,
            role='admin'
        ).exists()