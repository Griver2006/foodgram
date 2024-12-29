import os
import json
from pathlib import Path

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = ('Импортирует ингредиенты из ingredients.json '
            'или ingredients.csv в базу данных')

    def handle(self, *args, **kwargs):
        data_dir = os.path.join(Path(
            __file__
        ).resolve().parent.parent.parent.parent, 'data')

        json_file = os.path.join(data_dir, 'ingredients.json')
        if os.path.exists(json_file):
            self.import_from_json(json_file)
        else:
            self.stdout.write('backend/data/ingredients.json не найден')

    def import_from_json(self, file_path):
        """Импорт из JSON файла"""
        self.stdout.write(f'Импорт данных из {file_path}...')

        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)

            # Собираем объекты для массового создания
            ingredients = []
            existing_ingredients = set(
                Ingredient.objects.values_list('name', flat=True)
            )  # Загружаем существующие

            for item in data:
                # Добавляем только новые
                if item['name'] not in existing_ingredients:
                    ingredients.append(
                        Ingredient(
                            name=item['name'],
                            measurement_unit=item['measurement_unit']
                        )
                    )

            if ingredients:
                Ingredient.objects.bulk_create(
                    ingredients, ignore_conflicts=True
                )

        self.stdout.write(self.style.SUCCESS('Импорт из JSON завершен!'))
