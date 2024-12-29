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
    readonly_fields = ('favorite_count', 'short_link')
    search_fields = ('name', 'author__username')
    list_filter = ('tags', )
    inlines = (RecipeIngredientInline,)

    def short_link(self, obj):
        if obj.short_link:
            return obj.short_link
        return 'Ссылка появится после сохранения'


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')


admin.site.register(Tag)
admin.site.register(FavouriteRecipe)
admin.site.register(Follow)
admin.site.register(ShoppingList)
