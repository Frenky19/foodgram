from django.apps import AppConfig


class UsersConfig(AppConfig):
    """Конфигурация приложения для работы с пользователями."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    verbose_name = 'Пользователи'
