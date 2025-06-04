from django.core.validators import RegexValidator

from utils.constants import (ALLOWED_CHARS_FOR_MODELS_NAMES,
                             ALLOWED_SYMBOLS_FOR_USERNAME)


models_names_validator = RegexValidator(
    regex=ALLOWED_CHARS_FOR_MODELS_NAMES,
    message='Недопустимые символы.',
    flags=0
)

username_validator = RegexValidator(
    regex=ALLOWED_SYMBOLS_FOR_USERNAME,
    message='Недопустимые символы в имени пользователя.',
    flags=0
)
