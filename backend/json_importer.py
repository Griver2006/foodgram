import json

from recipes.models import Ingredient


with open('../data/ingredients.json', encoding='UTF-8') as f:
    parsed_data = json.load(f)


ingredients = [Ingredient(name=data['name'], measurement_unit=data['measurement_unit']) for data in parsed_data]
Ingredient.objects.bulk_create(ingredients)
