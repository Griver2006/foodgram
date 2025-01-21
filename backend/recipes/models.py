from hashids import Hashids

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator

from api.constants import (
    MAX_CHAR_LENGTH,
    MAX_LENGTH_SHORT_LINK,
    MAX_TAG_NAME_CHAR_LENGTH,
    MAX_TAG_SLUG_CHAR_LENGTH,
    MAX_INGREDIENT_NAME_CHAR_LENGTH,
    MAX_INGREDIENT_MEASUREMENT_UNIT_CHAR_LENGTH,
    MIN_INGREDIENT_AMOUNT_QUANTITY,
    MIN_HASHIDS_LENGTH,
    MIN_COOKING_TIME,
    STR_OUTPUT_SLICE,
)


User = get_user_model()
hashids = Hashids(min_length=MIN_HASHIDS_LENGTH)


class Recipe(models.Model):
    """Модель 'Рецепта'."""

    name = models.CharField(
        max_length=MAX_CHAR_LENGTH,
        verbose_name='Название'
    )
    text = models.TextField(
        verbose_name='Описание'
    )
    ingredients = models.ManyToManyField(
        'Ingredient',
        through='RecipeIngredient',
        related_name='ingredients',
        verbose_name='Ингредиенты'
    )
    tags = models.ManyToManyField(
        'Tag',
        verbose_name='Теги',
    )
    cooking_time = models.PositiveSmallIntegerField(
        validators=(MinValueValidator(
            MIN_COOKING_TIME, message='Время готовки не может быть меньше 1'
            ),
        ),
        verbose_name='Время приготовления',
    )
    image = models.ImageField(
        upload_to='recipes/images/',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='recipes',
        verbose_name='Автор'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Добавлено'
    )
    short_link = models.CharField(
        max_length=MAX_LENGTH_SHORT_LINK,
        blank=True,
        unique=True,
        null=True
    )

    class Meta:
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-created_at',)

    def save(self, *args, **kwargs):
        if self.pk is None:
            super().save(*args, **kwargs)
            self.short_link = hashids.encode(self.pk)
            self.save()
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return self.name[:STR_OUTPUT_SLICE]


class Tag(models.Model):
    """Модель 'Тега'."""

    name = models.CharField(
        max_length=MAX_TAG_NAME_CHAR_LENGTH,
        unique=True,
        verbose_name='Название'
    )
    slug = models.SlugField(
        unique=True,
        max_length=MAX_TAG_SLUG_CHAR_LENGTH,
        verbose_name='Слаг'
    )

    class Meta:
        verbose_name = 'тег'
        verbose_name_plural = 'Теги'

    def __str__(self):
        return self.name[:STR_OUTPUT_SLICE]


class Ingredient(models.Model):
    """Модель 'Ингридиента'."""

    name = models.CharField(
        max_length=MAX_INGREDIENT_NAME_CHAR_LENGTH,
        verbose_name='Название'
    )
    measurement_unit = models.CharField(
        max_length=MAX_INGREDIENT_MEASUREMENT_UNIT_CHAR_LENGTH,
        verbose_name='Мера измерения'
    )

    class Meta:
        verbose_name = 'ингридиент'
        verbose_name_plural = 'Ингридиенты'
        constraints = (
            models.UniqueConstraint(
                fields=('name', 'measurement_unit'),
                name='unique_name_measurement_unit'
            ),
        )

    def __str__(self):
        return self.name[:STR_OUTPUT_SLICE]


class RecipeIngredient(models.Model):
    """Связующая модель 'Рецепт' и 'Ингридиент'."""

    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='recipe_ingredients',
        verbose_name='Рецепт'
    )
    ingredient = models.ForeignKey(
        Ingredient,
        on_delete=models.CASCADE,
        verbose_name='Ингредиент'
    )
    amount = models.PositiveIntegerField(
        validators=(MinValueValidator(
            MIN_INGREDIENT_AMOUNT_QUANTITY,
            message='Количество ингредиента не может быть меньше 1'
            ),
        ),
        verbose_name='Количество',
    )

    class Meta:
        constraints = (
            models.UniqueConstraint(
                fields=('recipe', 'ingredient'),
                name='unique_recipe_ingredient'
            ),
        )

    def __str__(self):
        return (f'Ингредиент "{self.ingredient.name} {self.amount}'
                f' {self.ingredient.measurement_unit}"'
                f' в рецепте "{self.recipe}"')


class BaseUserRecipeRelation(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт',
    )

    class Meta:
        abstract = True
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='%(class)s_unique_user_recipe'
            ),
        )

    def __str__(self):
        return self._meta.verbose_name


class FavouriteRecipe(BaseUserRecipeRelation):
    """Связующая модель для 'Избранных рецептов'."""

    class Meta(BaseUserRecipeRelation.Meta):
        default_related_name = 'favourites'
        verbose_name = 'избранное'
        verbose_name_plural = 'Избранные'


class ShoppingList(BaseUserRecipeRelation):
    """Связующая модель для 'Списка покупок'."""

    class Meta(BaseUserRecipeRelation.Meta):
        default_related_name = 'purchases'
        verbose_name = 'покупка'
        verbose_name_plural = 'Список покупок'
