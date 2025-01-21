from io import BytesIO


def get_shopping_cart_file_buffer(recipes, total_ingredients):
    content = ''

    for recipe in recipes:
        content += (
            f'Название: {recipe["recipe__name"]}\n'
            f'Время приготовления: {recipe["recipe__cooking_time"]}\n\n'
        )

    content += 'Список всех ингредиентов:\n'

    for item in total_ingredients:
        content += (
            f'  - {item["ingredient__name"]} '
            f'({item["ingredient__measurement_unit"]}) — '
            f'{item["total_amount"]}\n'
        )

    text_content = content
    file_buffer = BytesIO()
    file_buffer.write(text_content.encode('utf-8'))
    file_buffer.seek(0)

    return file_buffer
