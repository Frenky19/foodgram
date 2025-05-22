from django.apps import AppConfig


class MealsConfig(AppConfig):
    """Конфиг приложения блюд."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'meals'
    verbose_name = 'Блюда'
