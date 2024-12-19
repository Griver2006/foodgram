from django_filters import rest_framework as filters

from api.models import Recipe


class RecipeFilter(filters.FilterSet):
    is_favorited = filters.BooleanFilter(method='filter_by_is_favorited')
    is_in_shopping_cart = filters.BooleanFilter(method='filter_by_is_in_shopping_cart')
    tags = filters.CharFilter(method='filter_by_tags')

    class Meta:
        model = Recipe
        fields = ('author', 'is_favorited', 'is_in_shopping_cart', 'tags')

    def filter_by_is_favorited(self, queryset, name, value):
        user = self.request.user

        if value:
            return queryset.filter(favouriterecipe__user=user)

        return queryset

    def filter_by_is_in_shopping_cart(self, queryset, name, value):
        user = self.request.user

        if value:
            return queryset.filter(shoppinglist__user=user)

        return queryset

    def filter_by_tags(self, queryset, name, value):
        tag_slugs = self.request.query_params.getlist('tags')
        if tag_slugs:
            queryset = queryset.filter(tags__slug__in=tag_slugs).distinct()
        return queryset
