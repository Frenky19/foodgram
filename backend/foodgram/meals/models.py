from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.text import Truncator, slugify

from users.models import User
from utils.constants import (LIMIT_OF_SYMBOLS, INGREDIENT_NAME_LIMIT,
                             UNIT_LIMIT, TAG_NAME_LIMIT, TAG_SLUG_LIMIT,
                             UNIT_LIMIT, RECIPE_NAME_LIMIT, DESCRIPTION_LIMIT,
                             MIN_AMOUNT, MIN_COOK_TIME, MAX_DIGITS_FOR_AMOUNT,
                             DECIMAL_PLACES_FOR_AMOUNT)


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
        verbose_name='Название ингридиента'
    )
    measurement_unit = models.CharField(
        max_length=UNIT_LIMIT,
        unique=True,
        choices=UNITS,
        verbose_name='Единица измерения'
    )

    class Meta:
        """Мета-класс для настроек модели ингредиента."""

        ordering = ['name']
        verbose_name = 'Ингридиент'
        verbose_name_plural = 'Ингридиенты'

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
        return (f'{Truncator(self.name).words(LIMIT_OF_SYMBOLS)}')


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
        verbose_name='Автор рецепта'
    )
    name = models.CharField(
        max_length=RECIPE_NAME_LIMIT,
        verbose_name='Название рецепта'
    )
    image = models.ImageField(
        upload_to='recipes/images/',
        null=True,
        blank=True,
        verbose_name='Изображение блюда'
    )
    description = models.TextField(
        max_length=DESCRIPTION_LIMIT,
        verbose_name='Описание рецепта'
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Тэг'
    )
    cook_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления в минутах',
        validators=[MinValueValidator(MIN_COOK_TIME)]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """Мета-класс для настроек модели рецепта."""

        ordering = ['name']
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        default_related_name = '%(class)ss'

    def __str__(self):
        """Строковое представление рецепта."""
        return Truncator(self.name).words(LIMIT_OF_SYMBOLS)


class RecipeIngredient(models.Model):
    """Связующая модель для ингредиентов в рецепте."""

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='ingredients',
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        related_name='ingredients',
        verbose_name='Ингредиент'
    )
    amount = models.DecimalField(
        verbose_name='Количество',
        validators=[MinValueValidator(Decimal(MIN_AMOUNT))],
        max_digits=MAX_DIGITS_FOR_AMOUNT,
        decimal_places=DECIMAL_PLACES_FOR_AMOUNT
    )

    class Meta:
        """Мета-класс для настроек связи рецепта и ингредиента."""

        verbose_name = 'Ингредиент для рецепта'
        verbose_name_plural = 'Ингредиенты для рецепта'

    def __str__(self):
        """Строковое представление с количеством и единицей измерения."""
        unit_disp = self.ingredient.get_unit_with_amount_display(self.amount)
        truncated_words = Truncator(unit_disp).words(LIMIT_OF_SYMBOLS)
        return (
            f'{Truncator(self.ingredient).words(LIMIT_OF_SYMBOLS)} - '
            f'{Truncator(self.amount).words(LIMIT_OF_SYMBOLS)} '
            f'{truncated_words}'
        )


class Favorite(models.Model):
    """Модель для хранения избранных рецептов пользователей."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )

    class Meta:
        """Мета-класс для настроек модели избранного."""

        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        default_related_name = '%(class)ss'

    def __str__(self):
        """Строковое представление избранного."""
        return (
            f'Рецепт {Truncator(self.recipe).words(LIMIT_OF_SYMBOLS)}'
            f' пользователя {Truncator(self.user).words(LIMIT_OF_SYMBOLS)}'
        )


class ShoppingCart(models.Model):
    """Модель корзины покупок с рецептами пользователя."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор',
        related_name='shopping_carts'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='in_shopping_cart',
        verbose_name='Рецепт'
    )

    class Meta:
        """Мета-класс для настроек корзины покупок."""

        verbose_name = 'Корзина покупок'
        verbose_name_plural = 'Корзина покупок'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_shopping_cart'
            )
        ]

    def __str__(self):
        """Строковое представление корзины покупок."""
        return (
            f'Рецепт {Truncator(self.recipe).words(LIMIT_OF_SYMBOLS)}'
            f' пользователя {Truncator(self.user).words(LIMIT_OF_SYMBOLS)}'
        )
