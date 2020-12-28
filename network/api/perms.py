"""SatNOGS Network API permissions, django rest framework"""
from rest_framework import permissions

from network.base.perms import schedule_perms


class SafeMethodsOnlyPermission(permissions.BasePermission):
    """Anyone can access non-destructive methods (like GET and HEAD)"""
    def has_permission(self, request, view):
        return self.has_object_permission(request, view)

    def has_object_permission(self, request, view, obj=None):
        return request.method in permissions.SAFE_METHODS


class StationOwnerPermission(permissions.BasePermission):
    """Only the owner can edit station jobs"""
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.method == 'POST' and schedule_perms(request.user):
            return True
        return (
            request.user.is_authenticated and obj.ground_station
            and request.user == obj.ground_station.owner
        )
