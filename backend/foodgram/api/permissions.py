from rest_framework import permissions


class IsAuthorOrReadOnly(permissions.BasePermission):
    """
    Разрешение на изменение только для автора.

    Остальным только чтение.
    """

    def has_object_permission(self, request, view, obj):
        """."""
        return (
            request.method in permissions.SAFE_METHODS
            or obj.author == request.user
        )


class IsAuthenticatedOrReadOnly(permissions.BasePermission):
    """
    Разрешение на создание только для авторизованных пользователей.

    Остальным только чтение.
    """

    def has_permission(self, request, view):
        """."""
        return (
            request.method in permissions.SAFE_METHODS
            or request.user.is_authenticated
        )
