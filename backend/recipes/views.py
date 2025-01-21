from django.shortcuts import get_object_or_404, redirect

from recipes.models import Recipe


def redirect_to_recipe(request, short_link):
    """
    Вьюшка, которая производит редирект от короткой ссылки на нужный url.
    """

    recipe = get_object_or_404(Recipe, short_link=short_link)
    # Перенаправляем на страницу рецепта
    return redirect(f'/recipes/{recipe.id}/')
