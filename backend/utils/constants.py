ALLOWED_SYMBOLS_FOR_USERNAME = r'^[\w.@+-]+\Z'
"""Допустимые символы для логина пользователя."""

ALLOWED_CHARS_FOR_MODELS_NAMES = r'^[a-zA-Zа-яА-ЯёЁ\s\'-]+$'
"""Допустимые симловы для имени и фамилии пользователя.

Включает буквы основных языков, апострофы, пробелы и дефисы.
"""

EMAIL_LIMIT = 254
"""Ограничение по длине для поля Email модели User."""

FIRST_NAME_LIMIT = 150
"""Ограничение по длине для поля first_name модели User."""

INGREDIENT_NAME_LIMIT = 128
"""Ограничение по длине для поля name модели Ingredient."""

LAST_NAME_LIMIT = 150
"""Ограничение по длине для поля last_name модели User."""

LIMIT_OF_SYMBOLS = 20
"""Ограничение по длине для строкового представления моделей."""

MEASUREMENT_UNIT_LIMIT = 64
"""Ограничение по длине для поля measurement_unit модели Ingredient."""

MIN_AMOUNT = 1
"""Ограничение на минимальное значение поля amount модели Ingredient."""

MAX_AMOUNT = 9999
"""Ограничение на максимальное значение поля amount модели Ingredient."""

MIN_COOK_TIME = 1
"""Ограничение на минимальное значение поля cooking_time модели Recipe."""

MAX_COOK_TIME = 1440
"""Ограничение на максимальное значение поля cooking_time модели Recipe.

1440 - один день
"""

PAGE_SIZE = 6
"""Количество объектов, отображаемых на странице."""

RECIPE_NAME_LIMIT = 256
"""Ограничение по длине для поля name модели Recipe."""

TAG_NAME_LIMIT = 32
"""Ограничение по длине для поля name модели Tag."""

TAG_SLUG_LIMIT = 32
"""Ограничение по длине для поля slug модели Recipe."""

USERNAME_LIMIT = 150
"""Ограничение по длине для поля username модели User."""
