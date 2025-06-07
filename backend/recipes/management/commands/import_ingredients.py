import csv
import logging

from django.core.management.base import BaseCommand
from django.db import IntegrityError

from foodgram import settings
from recipes.models import Ingredient

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Импорт данных из csv файла в базу данных."""

    def add_arguments(self, parser):
        """Добавляет аргументы командной строки для команды импорта."""
        parser.add_argument('--path', type=str, help='Path to file')

    def handle(self, *args, **options):
        """Обрабатывает команду импорта данных из CSV файла.

        Выполняет:
        1. Чтение указанного CSV файла
        2. Парсинг строк с данными об ингредиентах
        3. Создание объектов Ingredient в базе данных
        4. Обработку дубликатов и ошибок целостности
        5. Формирование отчета о результатах импорта
        """
        success_count = 0
        logger.info('Загрузка данных...')
        with open(
                f'{settings.BASE_DIR}/data/ingredients.csv',
                'r',
                encoding='utf-8',
        ) as csv_file:
            reader = csv.reader(csv_file)
            for row in reader:
                name_csv = 0
                unit_csv = 1
                try:
                    obj, created = Ingredient.objects.get_or_create(
                        name=row[name_csv],
                        measurement_unit=row[unit_csv],
                    )
                    if created:
                        success_count += 1
                    if not created:
                        logger.debug(f'Ингредиент {obj} уже в базе данных')
                except IntegrityError as err:
                    logger.error(f'Ошибка в строке {row}: {err}')
        logger.info(f'Успешно импортировано объектов: {success_count}')
