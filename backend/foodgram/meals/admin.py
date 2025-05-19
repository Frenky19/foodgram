from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from meals.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                          ShoppingCart, Tag)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    """Управление ингредиентами в админке."""

    list_display = ('name', 'unit')
    search_fields = ('name',)
    list_filter = ('unit',)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    """Управление тегами в админке."""

    list_display = ('name', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


class RecipeIngredientInline(admin.TabularInline):
    """Инлайн для редактирования ингредиентов в рецепте."""

    model = RecipeIngredient
    extra = 1
    autocomplete_fields = ('ingredient',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    """Управление рецептами в админке."""

    list_display = (
        'name',
        'meal_image_preview',
        'author',
        'cook_time',
        'favorites_count',
        'created_at'
    )
    search_fields = (
        'name',
        'author__username',
        'author__email'
    )
    list_filter = ('tags', 'created_at')
    inlines = (RecipeIngredientInline,)
    autocomplete_fields = ('tags',)
    readonly_fields = ('favorites_count', 'meal_image_preview')

    def get_queryset(self, request):
        """Оптимизированный QuerySet для админки рецептов.

        Выполняет:
        - Аннотацию количества добавлений в избранное
        - Оптимизацию запросов к связанным объектам:
        * select_related для автора (одиночные связи)
        * prefetch_related для тегов (множественные связи)
        """
        return super().get_queryset(request).annotate(
            favorites_count=Count('favorites')
        ).select_related('author').prefetch_related('tags')

    def favorites_count(self, obj):
        """Возвращает количество добавлений рецепта в избранное."""
        return obj.favorites_count
    favorites_count.admin_order_field = 'favorites_count'
    favorites_count.short_description = 'В избранном'

    def meal_image_preview(self, obj):
        """
        Отображает изображения блюда в админке.

        Возвращает:
            HTML-тег изображения, если файл существует, или текст-заглушку.
        """
        if obj.image:
            return format_html(
                ('<img src="{}" style="max-height:'
                 '100px; max-width: 100px;" />'),
                obj.image.url
            )
        return "Нет изображения"
    meal_image_preview.short_description = 'Фото блюда'


@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(admin.ModelAdmin):
    """Управление связями рецептов и ингредиентов в админке."""

    list_display = (
        'recipe', 'ingredient', 'amount', 'get_unit_with_dynamic'
    )
    autocomplete_fields = ('recipe',)

    def get_unit_with_dynamic(self, obj):
        """Отображение динамически изменяемых единиц измерений ингредиента."""
        return f'{obj.ingredient.get_unit_with_amount_display(obj.amount)}'
    get_unit_with_dynamic.short_description = 'Единица измерений'


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
class ShoppingCartAdmin(admin.ModelAdmin):
    """Управление корзинами для покупок."""

    list_display = ('recipe', 'user')
    search_fields = (
        'user__username',
        'recipe__name'
    )
    autocomplete_fields = ('user', 'recipe')
