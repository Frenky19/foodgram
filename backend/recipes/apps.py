from django.apps import AppConfig


class RecipesConfig(AppConfig):
    """Конфиг приложения рецептов."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'recipes'
    verbose_name = 'Рецепты'
