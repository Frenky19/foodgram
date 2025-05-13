from django.contrib.auth.models import AbstractUser
# from django.core.validators import RegexValidator
from django.db import models
from django.utils.text import Truncator
# from api.validators import validate_username
# from users.service import get_max_length
# from meals.constants import (ALLOWED_SYMBOLS_FOR_USERNAME, EMAIL_LENGTH,
#                               LIMIT_OF_SYMBOLS, USERNAME_LENGTH)
from meals.constants import LIMIT_OF_SYMBOLS


class User(AbstractUser):
    """."""

    profile_image = models.ImageField(
        upload_to='profile/images/',
        blank=True,
        null=True,
        verbose_name='Фото профиля'
    )

    class Meta:
        """."""

        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        """."""
        return Truncator(self.username).words(LIMIT_OF_SYMBOLS)
