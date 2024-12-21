from django_filters import rest_framework as filters
from django_filters import CharFilter

from recipes.models import Recipe, Ingredient


class RecipeFilter(filters.FilterSet):
    is_favorited = filters.BooleanFilter(method='filter_by_is_favorited')
    is_in_shopping_cart = filters.BooleanFilter(method='filter_by_is_in_shopping_cart')
    tags = filters.CharFilter(method='filter_by_tags')

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
            return queryset.filter(shoppinglist__user=user)

        return queryset

    def filter_by_tags(self, queryset, name, value):
        tag_slugs = self.request.query_params.getlist('tags')
        if tag_slugs:
            queryset = queryset.filter(tags__slug__in=tag_slugs).distinct()
        return queryset


class IngredientFilter(filters.FilterSet):
    name = CharFilter(field_name='name', lookup_expr='istartswith')

    class Meta:
        model = Ingredient
        fields = ('name',)
