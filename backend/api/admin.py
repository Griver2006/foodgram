from django.contrib import admin
from .models import Recipe, RecipeIngredient, Tag, Ingredient, FavouriteRecipe, Follow, ShoppingList


class RecipeIngredientInline(admin.StackedInline):
    model = RecipeIngredient
    extra = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    inlines = (RecipeIngredientInline,)


admin.site.register(Tag)
admin.site.register(Ingredient)
admin.site.register(FavouriteRecipe)
admin.site.register(Follow)
admin.site.register(ShoppingList)
