from django.contrib import admin
from django.contrib.auth.models import Group
from django.utils.safestring import mark_safe

from recipes.models import (
    Recipe,
    RecipeIngredient,
    Tag,
    Ingredient,
    FavouriteRecipe,
    ShoppingList
)


class RecipeIngredientInline(admin.StackedInline):
    model = RecipeIngredient
    min_num = 1
    validate_min = True
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'author',
        'get_ingredients',
        'get_tags',
        'get_image'
    )
    readonly_fields = (
        'get_favorite_count',
        'get_short_link'
    )
    exclude = (
        'short_link',
    )
    search_fields = (
        'name',
        'author__username'
    )
    list_filter = (
        'tags',
    )
    inlines = (RecipeIngredientInline,)

    def get_queryset(self, request):
        self.request = request

        return super().get_queryset(request).select_related('author')

    @admin.display(description='Короткая ссылка')
    def get_short_link(self, obj):
        if obj.pk:
            return self.request.build_absolute_uri(f'/s/{obj.short_link}')
        return 'Ссылка появится после сохранения'

    @admin.display(description='В избранном')
    def get_favorite_count(self, obj):
        return obj.favourites.count()

    @admin.display(description='Ингредиенты')
    def get_ingredients(self, obj):
        return ', '.join(obj.ingredients.values_list('name', flat=True))

    @admin.display(description='Теги')
    def get_tags(self, obj):
        return ', '.join(obj.tags.values_list('name', flat=True))

    @admin.display(description='Картинка')
    def get_image(self, obj):
        return mark_safe(f'<img src={obj.image.url} width="80" height="60">')


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')


admin.site.register(Tag)
admin.site.register(FavouriteRecipe)
admin.site.register(ShoppingList)

admin.site.unregister(Group)
