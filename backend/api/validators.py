from django.core.validators import RegexValidator

from utils.constants import (ALLOWED_CHARS_FOR_MODELS_NAMES,
                             ALLOWED_SYMBOLS_FOR_USERNAME)


def models_names_validator(message):
    """Проверяет допустимые символы в названиях полей моделей.

    Автоматически подставляет сообщение об ошибке в зависимости от поля,
    в котором были введены невалидные данные.
    """
    return RegexValidator(
        regex=ALLOWED_CHARS_FOR_MODELS_NAMES,
        message=message,
        flags=0
    )


username_validator = RegexValidator(
    regex=ALLOWED_SYMBOLS_FOR_USERNAME,
    message='Логин может содержать только буквы, цифры и символы @/./+/-/_;',
    flags=0
)
