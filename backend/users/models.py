from django.contrib.auth.models import AbstractUser
from django.db import models

from api.validators import models_names_validator, username_validator
from utils.constants import (EMAIL_LIMIT, FIRST_NAME_LIMIT, LAST_NAME_LIMIT,
                             USERNAME_LIMIT)


class User(AbstractUser):
    """Пользователь системы с расширенной функциональностью.

    Наследует все поля стандартной модели пользователя Django и добавляет:
    - Поле для загрузки аватара профиля
    - Кастомные методы строкового представления
    """

    username = models.CharField(
        max_length=USERNAME_LIMIT,
        unique=True,
        verbose_name='Логин пользователя',
        validators=[username_validator],
        error_messages={
            'unique': 'Пользователь с таким логином уже существует'
        }
    )
    email = models.EmailField(
        max_length=EMAIL_LIMIT,
        unique=True,
        verbose_name='Email',
        error_messages={'unique': 'Пользователь с таким email уже существует'}
    )
    first_name = models.CharField(
        max_length=FIRST_NAME_LIMIT,
        verbose_name='Имя',
        validators=[models_names_validator(
            'Имя должно содержать только буквы, апострофы, пробелы и дефисы;'
        )],
    )
    last_name = models.CharField(
        max_length=LAST_NAME_LIMIT,
        verbose_name='Фамилия',
        validators=[models_names_validator(
            'Фамилия должна содержать только буквы, '
            'апострофы, пробелы и дефисы;'
        )],
    )
    avatar = models.ImageField(
        upload_to='media/avatars/',
        blank=True,
        verbose_name='Фото профиля'
    )
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = (
        'username',
        'first_name',
        'last_name',
    )

    class Meta:
        """Настройки отображения и сортировки пользователей."""

        ordering = ('username',)
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        """Логин пользователя."""
        return self.username


class Subscription(models.Model):
    """Связь подписки между пользователем (подписчиком) и автором рецептов.

    Связывает двух пользователей отношениями «подписчик» -> «автор» с проверкой
    уникальности связи пользователей. Запрещает подписку на самого себя на
    уровне БД.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Подписчик'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='followers',
        verbose_name='Автор рецепта'
    )

    class Meta:
        """Настройки подписок."""

        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        constraints = [
            models.UniqueConstraint(
                fields=('user', 'author'),
                name='unique_follow',
                violation_error_message=(
                    'Вы уже подписаны на этого пользователя'
                )
            )
        ]

    def __str__(self):
        """Пользователь {подписчик} подписан на Пользователя {автор}."""
        return (
            f'Пользователь {self.user.username} подписан на Пользователя '
            f'{self.author.username}'
        )
