from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import Truncator, slugify

from utils.constants import (
    INGREDIENT_NAME_LIMIT, LIMIT_OF_SYMBOLS, MEASUREMENT_UNIT_LIMIT,
    MIN_AMOUNT, MIN_COOK_TIME, RECIPE_NAME_LIMIT, TAG_NAME_LIMIT,
    TAG_SLUG_LIMIT, TEXT_LIMIT)

User = get_user_model()


# Надо доработать валидацию разрешенных символов для всех моделей
class Ingredient(models.Model):
    """Модель ингредиента с возможностью выбора единиц измерения."""

    UNITS = [
        ('Гр', 'Граммы'),
        ('Кг', 'Килограммы'),
        ('Мл', 'Миллилитры'),
        ('Л', 'Литры'),
        ('Шт', 'Штуки'),
        ('СЛ', 'Столовые ложки'),
        ('ЧЛ', 'Чайные ложки'),
    ]

    UNIT_FORMS = {
        'Гр': ['грамм', 'грамма', 'граммов'],
        'Кг': ['килограмм', 'килограмма', 'килограммов'],
        'Мл': ['миллилитр', 'миллилитра', 'миллилитров'],
        'Л': ['литр', 'литра', 'литров'],
        'Шт': ['штука', 'штуки', 'штук'],
        'СТ': ['столовая ложка', 'столовые ложки', 'столовых ложек'],
        'ЧЛ': ['чайная ложка', 'чайные ложки', 'чайных ложек'],
    }

    name = models.CharField(
        max_length=INGREDIENT_NAME_LIMIT,
        unique=True,
        verbose_name='Название ингредиента'
    )
    measurement_unit = models.CharField(
        max_length=MEASUREMENT_UNIT_LIMIT,
        verbose_name='Единица измерения'
    )

    class Meta:
        """Мета-класс для настроек модели ингредиента."""

        ordering = ['name']
        verbose_name = 'Ингридиент'
        verbose_name_plural = 'Ингридиенты'
        constraints = (
            models.UniqueConstraint(
                fields=('name', 'measurement_unit'),
                name='unique_ingredient',
            ),
        )

    def get_unit_with_amount_display(self, amount):
        """
        Возвращает правильную грамматическую форму единицы измерения.

        Args:
            amount (float): Количество ингредиента

        Returns:
            str: Склоненная форма единицы измерения
        """
        unit_forms = self.UNIT_FORMS.get(self.measurement_unit, ['', '', ''])
        n = abs(amount) % 100
        n1 = n % 10
        if 10 < n < 20:
            return unit_forms[2]
        elif 1 < n1 < 5:
            return unit_forms[1]
        elif n1 == 1:
            return unit_forms[0]
        else:
            return unit_forms[2]

    def __str__(self):
        """Строковое представление ингредиента."""
        return (
            f'{Truncator(self.name).words(LIMIT_OF_SYMBOLS)}'
            f'({self.measurement_unit})'
        )


class Tag(models.Model):
    """Модель тега для категоризации рецептов."""

    name = models.CharField(
        max_length=TAG_NAME_LIMIT,
        unique=True,
        verbose_name='Название'
    )
    slug = models.SlugField(
        max_length=TAG_SLUG_LIMIT,
        unique=True,
        help_text=(
            'Человекочитаемое название страницы для URL; '
            'разрешены символы латиницы, цифры, дефис и подчёркивание.'
        ),
        verbose_name='Слаг'
    )

    class Meta:
        """Мета-класс для настроек модели тега."""

        ordering = ['name']
        verbose_name = 'Тэг'
        verbose_name_plural = 'Тэги'

    def save(self, *args, **kwargs):
        """Автоматически генерирует slug из названия при сохранении."""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        """Строковое представление тега."""
        return Truncator(self.name).words(LIMIT_OF_SYMBOLS)


class Recipe(models.Model):
    """Модель рецепта с привязкой к автору и тегам."""

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор рецепта',
    )
    name = models.CharField(
        max_length=RECIPE_NAME_LIMIT,
        verbose_name='Название рецепта'
    )
    image = models.ImageField(
        upload_to='media/recipes/',
        null=True,
        blank=True,
        verbose_name='Изображение блюда'
    )
    text = models.TextField(
        max_length=TEXT_LIMIT,
        verbose_name='Описание рецепта'
    )
    tags = models.ManyToManyField(
        Tag,
        through='RecipeTags',
        verbose_name='Тэг'
    )
    cooking_time = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(
            MIN_COOK_TIME,
            f'Время готовки не может быть менее {MIN_COOK_TIME} минут(ы)'
        ), ],
        verbose_name='Время приготовления в минутах',
    )

    class Meta:
        """Мета-класс для настроек модели рецепта."""

        ordering = ['-id']
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        default_related_name = 'recipes'

    def __str__(self):
        """Строковое представление рецепта."""
        return Truncator(self.name).words(LIMIT_OF_SYMBOLS)


class RecipeIngredient(models.Model):
    """Связующая модель для ингредиентов в рецепте."""

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='ingredient_list',
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='ingredient_recipe',
        verbose_name='Ингредиент'
    )
    amount = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(
            MIN_AMOUNT,
            message=f'Минимальное количество ингредиента - {MIN_AMOUNT}'
        )],
        verbose_name='Количесво ингредиента',
    )

    class Meta:
        """Мета-класс для настроек связи рецепта и ингредиента."""

        verbose_name = 'Ингредиент для рецепта'
        verbose_name_plural = 'Ингредиенты для рецепта'
        constraints = (
            models.UniqueConstraint(
                fields=('ingredient', 'recipe'),
                name='unique_recipe_ingredient',
            ),
        )

    def __str__(self):
        """Строковое представление с количеством и единицей измерения."""
        unit_disp = self.ingredient.get_unit_with_amount_display(self.amount)
        truncated_words = Truncator(unit_disp).words(LIMIT_OF_SYMBOLS)
        return (
            f'{Truncator(self.ingredient).words(LIMIT_OF_SYMBOLS)} - '
            f'{Truncator(self.amount).words(LIMIT_OF_SYMBOLS)} '
            f'{truncated_words}'
        )


class RecipeTags(models.Model):
    """Связующая модель для тэгов в рецепте."""

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='tag_list',
        verbose_name='Рецепт'
    )
    tag = models.ForeignKey(
        Tag,
        on_delete=models.CASCADE,
        related_name='tag_recipe',
        verbose_name='Тэг'
    )

    class Meta:
        """Мета-класс для настроек связи рецепта и тэга."""

        verbose_name = 'Тэг рецепта'
        verbose_name_plural = 'Тэги рецепта'
        constraints = [
            models.UniqueConstraint(fields=('recipe', 'tag'),
                                    name='unique_recipe_tag')
        ]

    def __str__(self):
        """Строковое представление рецепта с тэгом."""
        return f'Рецепт {self.recipe.name} (тэг {self.tag.name})'


class FavoriteShoppingCartBaseModel(models.Model):
    """
    Базовая модель для избранного и корзины покупок.

    Предоставляет общую структуру для хранения отношений между пользователями
    и рецептами с гарантией уникальности каждой пары (пользователь, рецепт).
    Предназначена для наследования конкретными моделями
    (Favorite и ShoppingCart).
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
    )

    class Meta:
        """Мета-класс для настройки базовой модели."""

        abstract = True
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='%(app_label)s_%(class)s_unique_user_recipe',
                violation_error_message='Рецепт уже добавлен'
            )
        ]

    def __str__(self):
        """Строковое представление связи в формате: Рецепт (Пользователь)."""
        return f'{self.recipe.name} ({self.user.username})'


class Favorite(FavoriteShoppingCartBaseModel):
    """Модель для хранения избранных рецептов пользователей."""

    class Meta(FavoriteShoppingCartBaseModel.Meta):
        """Мета-класс для настроек модели избранного."""

        verbose_name = 'Избранный'
        verbose_name_plural = 'Избранное'
        default_related_name = 'favorites'


class ShoppingCart(FavoriteShoppingCartBaseModel):
    """Модель корзины покупок с рецептами пользователя."""

    class Meta(FavoriteShoppingCartBaseModel.Meta):
        """Мета-класс для настроек корзины покупок."""

        verbose_name = 'Корзина покупок'
        verbose_name_plural = 'Корзины покупок'
        default_related_name = 'shopping_carts'
