from django.contrib import admin
from recipes.models import Recipe, RecipeIngredient, Tag, Ingredient, FavouriteRecipe, Follow, ShoppingList


class RecipeIngredientInline(admin.StackedInline):
    model = RecipeIngredient
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('name', 'author')
    readonly_fields = ('favorite_count',)
    search_fields = ('name', 'author__username')
    list_filter = ('tags', )
    inlines = (RecipeIngredientInline,)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('name', 'measurement_unit')


admin.site.register(Tag)
admin.site.register(FavouriteRecipe)
admin.site.register(Follow)
admin.site.register(ShoppingList)
