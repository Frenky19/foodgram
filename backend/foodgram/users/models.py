from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.text import Truncator
from utils.constants import LIMIT_OF_SYMBOLS


class User(AbstractUser):
    """Модель пользователя системы с расширенной функциональностью.

    Наследует все поля стандартной модели пользователя Django и добавляет:
    - Поле для загрузки аватара профиля
    - Кастомные методы строкового представления
    """

    profile_image = models.ImageField(
        upload_to='profile/images/',
        blank=True,
        null=True,
        verbose_name='Фото профиля'
    )

    class Meta:
        """Мета-класс для настройки модели пользователя."""

        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        """Строковое представление пользователя.

        Возвращает:
            str: Усеченное имя пользователя до LIMIT_OF_SYMBOLS символов
        """
        return Truncator(self.username).words(LIMIT_OF_SYMBOLS)


class Subscription(models.Model):
    """Модель для хранения информации о подписках пользователей.

    Связывает двух пользователей отношениями «подписчик» -> «автор» с проверкой
    уникальности связи пользователей. Запрещает подписку на самого себя на
    уровне БД.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Подписчик'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name='Автор рецепта'
    )

    class Meta:
        """Мета-класс для настройки модели подписок."""

        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'author'],
                name='unique_subscription'
            )
        ]

    def __str__(self):
        """Строковое представление подписки.

        Возвращает:
            str: Форматированная строка вида
            "Пользователь ___ подписан на Пользователь ___"
            с обрезанными именами до LIMIT_OF_SYMBOLS
        """
        return (
            f'Пользователь {Truncator(self.user).words(LIMIT_OF_SYMBOLS)}'
            'подписан на пользователя'
            f'{Truncator(self.author).words(LIMIT_OF_SYMBOLS)}'
        )
