from django.apps import AppConfig


class ApiConfig(AppConfig):
    """Конфиг приложения API."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'api'
