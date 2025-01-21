from django_filters import rest_framework as filters
from django_filters import CharFilter, ModelMultipleChoiceFilter

from recipes.models import Ingredient, Recipe, Tag


class RecipeFilter(filters.FilterSet):
    is_favorited = filters.BooleanFilter(
        method='filter_by_is_favorited'
    )
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_by_is_in_shopping_cart'
    )
    tags = ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        field_name='tags__slug',
        to_field_name='slug',
    )

    class Meta:
        model = Recipe
        fields = ('author', 'is_favorited', 'is_in_shopping_cart', 'tags')

    def filter_by_is_favorited(self, queryset, name, value):
        user = self.request.user

        if value and user.is_authenticated:
            return queryset.filter(favourites__user=user)

        return queryset

    def filter_by_is_in_shopping_cart(self, queryset, name, value):
        user = self.request.user

        if value and user.is_authenticated:
            return queryset.filter(purchases__user=user)

        return queryset


class IngredientFilter(filters.FilterSet):
    name = CharFilter(field_name='name', lookup_expr='istartswith')

    class Meta:
        model = Ingredient
        fields = ('name',)
