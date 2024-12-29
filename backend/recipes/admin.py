from django.contrib import admin

from recipes.models import (
    Recipe,
    RecipeIngredient,
    Tag,
    Ingredient,
    FavouriteRecipe,
    Follow,
    ShoppingList
)
from recipes.forms import (
    RecipeForm,
    RecipeIngredientInlineFormSet,
    RecipeIngredientInlineForm
)


class RecipeIngredientInline(admin.StackedInline):
    model = RecipeIngredient
    form = RecipeIngredientInlineForm
    formset = RecipeIngredientInlineFormSet
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    form = RecipeForm
    list_display = ('name', 'author')
    readonly_fields = ('favorite_count', 'get_short_link')
    exclude = ('short_link', )
    search_fields = ('name', 'author__username')
    list_filter = ('tags', )
    inlines = (RecipeIngredientInline,)

    def get_queryset(self, request):
        self.request = request  # Сохраняем request для дальнейшего использования
        return super().get_queryset(request)

    def get_short_link(self, obj):
        request = self.request  # Получаем request из Admin
        if request and obj.pk and obj.short_link:
            return request.build_absolute_uri(f'/s/{obj.short_link}')

        return 'Ссылка появится после сохранения'

    get_short_link.short_description = 'Короткая ссылка'


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')


admin.site.register(Tag)
admin.site.register(FavouriteRecipe)
admin.site.register(Follow)
admin.site.register(ShoppingList)
