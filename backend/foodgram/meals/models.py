from django.contrib.auth import get_user_model
from django.db import models
from django.core.validators import MinValueValidator
from django.utils.text import Truncator, slugify
from meals.constants import LIMIT_OF_SYMBOLS
from users.models import User


class Ingredient(models.Model):
    """Модель Ингридиента."""

    UNITS = [
        ('g', 'Граммы'),
        ('kg', 'Килограммы'),
        ('ml', 'Миллилитры'),
        ('l', 'Литр'),
        ('item', 'Штуки'),
        ('tbsp', 'Столовая ложка'),
        ('tsp', 'Чайная ложка'),
    ]

    UNIT_FORMS = {
        'g': ['грамм', 'грамма', 'граммов'],
        'kg': ['килограмм', 'килограмма', 'килограммов'],
        'ml': ['миллилитр', 'миллилитра', 'миллилитров'],
        'l': ['литр', 'литра', 'литров'],
        'item': ['штука', 'штуки', 'штук'],
        'tbsp': ['столовая ложка', 'столовые ложки', 'столовых ложек'],
        'tsp': ['чайная ложка', 'чайные ложки', 'чайных ложек'],
    }

    name = models.CharField(
        max_length=128,
        unique=True,
        verbose_name='Название ингридиента'
    )
    unit = models.CharField(
        max_length=64,
        unique=True,
        choices=UNITS,
        verbose_name='Единица измерения'
    )

    class Meta:
        """."""

        ordering = ['name']
        verbose_name = 'Ингридиент'
        verbose_name_plural = 'Ингридиенты'

    def get_unit_dynamic(self, amount):
        """Возвращает правильную форму единицы измерения для числа 'amount'."""
        unit_forms = self.UNIT_FORMS.get(self.unit, ['', '', ''])
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
        """Возвращает ограниченное строковое представление Ингридиента."""
        return (
            f'{Truncator(self.name).words(LIMIT_OF_SYMBOLS)} -'
            f'{Truncator(self.get_unit_dynamic()).words(LIMIT_OF_SYMBOLS)}'
        )


class Tag(models.Model):
    """Модель Тэга."""

    name = models.CharField(
        max_length=32,
        unique=True,
        verbose_name='Название'
    )
    slug = models.SlugField(
        max_length=32,
        unique=True,
        help_text=(
            'Человекочитаемое название страницы для URL; '
            'разрешены символы латиницы, цифры, дефис и подчёркивание.'
        ),
        verbose_name='Слаг'
    )

    class Meta:
        """."""

        ordering = ['name']
        verbose_name = 'Тэг'
        verbose_name_plural = 'Тэги'

    def save(self, *args, **kwargs):
        """Автоматически генерирует слаг из названия Тэга."""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        """Возвращает ограниченное строковое представление Тэга."""
        return Truncator(self.name).words(LIMIT_OF_SYMBOLS)


class Recipe(models.Model):
    """Модель Рецепта."""

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Автор рецепта'
    )
    name = models.CharField(
        max_length=256,
        verbose_name='Название рецепта'
    )
    image = models.ImageField(
        upload_to='recipes/images/',
        null=True,
        blank=True,
        verbose_name='Изображение блюда'
    )
    description = models.TextField(
        max_length=512,
        verbose_name='Описание рецепта'
    )
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Тэг'
    )
    cook_time = models.PositiveSmallIntegerField(
        verbose_name='Время приготовления в минутах',
        validators=[MinValueValidator(1)]
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        """."""

        ordering = ['name']
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        default_related_name = '%(class)ss'

    def __str__(self):
        """Возвращает ограниченное строковое представление Рецепта."""
        return Truncator(self.name).words(LIMIT_OF_SYMBOLS)


class RecipeIngredient(models.Model):
    """Промежуточная модель для связи кол-ва Ингридиента и Рецепта."""

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент'
    )
    amount = models.PositiveSmallIntegerField(
        verbose_name='Количество',
        validators=[MinValueValidator(1)]
    )

    class Meta:
        """."""

        verbose_name = 'Ингредиент рецепта'
        verbose_name_plural = 'Ингредиенты рецепта'

    def __str__(self):
        """Возвращает строковое представление количества ингридиента."""
        return f'{self.ingredient} - {self.amount}'


class Favorite(models.Model):
    """."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE
    )


class ShoppingCart(models.Model):
    """."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='shopping_carts'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='in_shopping_cart'
    )

    class Meta:
        """."""

        constraints = [
            models.UniqueConstraint(
                fields=['user', 'recipe'],
                name='unique_shopping_cart'
            )
        ]
