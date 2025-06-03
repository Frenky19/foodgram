from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """Управление ингредиентами в админке."""

    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)
    list_filter = ('measurement_unit',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Управление тегами в админке."""

    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


class RecipeIngredientInline(admin.TabularInline):
    """Редактирования ингредиентов в рецепте."""

    model = RecipeIngredient
    extra = 1
    autocomplete_fields = ('ingredient',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Управление рецептами в админке."""

    list_display = (
        'name',
        'recipe_image_preview',
        'author',
        'cooking_time',
        'favorite_count',
    )
    search_fields = (
        'name',
        'author__username',
        'author__email'
    )
    list_filter = ('tags',)
    inlines = (RecipeIngredientInline,)
    autocomplete_fields = ('tags',)
    readonly_fields = ('favorite_count', 'recipe_image_preview')

    def get_queryset(self, request):
        """Оптимизирует админку рецептов.

        Выполняет:
        - Аннотацию количества добавлений в избранное
        - Оптимизацию запросов к связанным объектам:
        * select_related для автора (одиночные связи)
        * prefetch_related для тегов (множественные связи)
        """
        return super().get_queryset(request).annotate(
            favorite_count=Count('favorites')
        ).select_related('author').prefetch_related('tags')

    def favorite_count(self, obj):
        """Возвращает количество добавлений рецепта в избранное."""
        return obj.favorite_count
    favorite_count.admin_order_field = 'favorite_count'
    favorite_count.short_description = 'В избранном'

    def recipe_image_preview(self, obj):
        """Отображание изображения блюда в админке.

        Возвращает:
            HTML-тег изображения, если файл существует, или текст-заглушку.
        """
        if obj.image:
            return format_html(
                ('<img src="{}" style="max-height:'
                 '100px; max-width: 100px;" />'),
                obj.image.url
            )
        return 'Нет изображения'
    recipe_image_preview.short_description = 'Фото блюда'


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    """Управление избранными рецептами в админке."""

    list_display = ('recipe', 'user')
    search_fields = (
        'user__username',
        'recipe__name'
    )
    autocomplete_fields = ('user', 'recipe')


@admin.register(ShoppingCart)
class ShoppingListAdmin(admin.ModelAdmin):
    """Управление корзинами для покупок."""

    list_display = ('recipe', 'user')
    search_fields = (
        'user__username',
        'recipe__name'
    )
    autocomplete_fields = ('user', 'recipe')
