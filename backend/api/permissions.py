from rest_framework import permissions


class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Разрешение, которое позволяет только владельцу объекта 
    редактировать его, а всем остальным — только читать.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.author == request.user


class IsAdminOnly(permissions.BasePermission):
    """
    Разрешение, которое позволяет только администраторам 
    выполнять любые действия.
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        if user and user.is_authenticated and user.is_staff:
            return True
        return False

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        if user and user.is_authenticated and user.is_staff:
            return True
        return False
