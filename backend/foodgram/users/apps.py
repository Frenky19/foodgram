from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Конфиг приложения пользователей."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    verbose_name = 'Пользователи'
