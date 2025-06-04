from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdminAuthorOrReadOnly(BasePermission):
    """Предоставление ограниченного доступа.

    - Чтение (безопасные методы) для всех пользователей (включая анонимных)
    - Запись (изменение данных) только:
        • Аутентифицированным пользователям для создания объектов (POST)
        • Автору объекта или администраторам для изменения/удаления
            (PUT/PATCH/DELETE)
    """

    def has_permission(self, request, view):
        """Проверяет разрешения на уровне запроса (до получения объекта).

        Args:
            request (HttpRequest): Объект запроса
            view (APIView): Обрабатываемое представление

        Returns:
            bool: True если доступ разрешен, False если запрещен
        """
        return (
            request.method in SAFE_METHODS
            or request.user.is_authenticated
        )

    def has_object_permission(self, request, view, obj):
        """Проверяет разрешения на уровне конкретного объекта.

        Args:
            request (HttpRequest): Объект запроса
            view (APIView): Обрабатываемое представление
            obj: Проверяемый объект модели

        Returns:
            bool: True если доступ разрешен, False если запрещен
        """
        return (
            request.method in SAFE_METHODS
            or obj.author == request.user
            or request.user.is_superuser
        )
