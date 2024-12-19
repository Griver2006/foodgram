from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError

from api.constants import MAX_CHAR_LENGTH, STR_OUTPUT_SLICE


class User(AbstractUser):
    """Кастомная модель юзера."""

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = (
        'username',
        'first_name',
        'last_name'
    )

    email = models.EmailField(
        unique=True,
        verbose_name='Электронная почта'
    )
    avatar = models.ImageField(
        upload_to='users/',
        default='users/avatar-icon.png'
    )
    follow = models.ManyToManyField(
        'self',
        through='Follow',
        symmetrical=False,
        verbose_name='Подписки'
    )
    favourite_recipes = models.ManyToManyField(
        'Recipe',
        through='FavouriteRecipe',
        verbose_name='Избранное'
    )

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)


class Follow(models.Model):
    """Связующая модель для подписок пользователей друг на друга."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name='Пользователь'
    )
    following = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='followers',
        verbose_name='Подписка'
    )

    class Meta:
        verbose_name = 'подписка'
        verbose_name_plural = 'Подписки'
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'following'),
                name='unique_name_owner'
            ),
        )

    def clean(self):
        if self.user == self.following:
            raise ValidationError(
                'Пользователь не может подписаться сам на себя.'
            )

    def save(self, *args, **kwargs):
        self.clean()
        super(Follow, self).save(*args, **kwargs)

    def __str__(self):
        return self.following.username[:STR_OUTPUT_SLICE]


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
        verbose_name='Время приготовления'
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
    is_published = models.BooleanField(
        default=True,
        verbose_name='Опубликовано',
        help_text='Снимите галочку, чтобы скрыть рецепт.'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Добавлено'
    )
    short_link = models.CharField(max_length=255, blank=True, unique=True)

    class Meta:
        verbose_name = 'рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ('-created_at',)

    def __str__(self):
        return self.name[:STR_OUTPUT_SLICE]


class Tag(models.Model):
    """Модель 'Тега'."""

    name = models.CharField(
        max_length=MAX_CHAR_LENGTH,
        unique=True,
        verbose_name='Название'
    )
    slug = models.SlugField(
        unique=True,
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
        max_length=MAX_CHAR_LENGTH,
        verbose_name='Название'
    )
    measurement_unit = models.CharField(
        max_length=MAX_CHAR_LENGTH,
        verbose_name='Мера измерения'
    )

    class Meta:
        verbose_name = 'ингридиент'
        verbose_name_plural = 'Ингридиенты'

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
        verbose_name='Количество',
    )


class FavouriteRecipe(models.Model):
    """Связующая модель для 'Избранных рецептов'."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='favourites',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Избранное'
    )

    class Meta:
        verbose_name = 'избранное'
        verbose_name_plural = 'Избранные'
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_user_favourite'
            ),
        )

    def __str__(self):
        return (f'Рецепт "{self.recipe.name}" в избранных'
                f' у пользователя "{self.user.username}"')


class ShoppingList(models.Model):
    """Связующая модель для 'Списка покупок'."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='purchases',
        verbose_name='Пользователь'
    )
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        verbose_name='Рецепт'
    )

    class Meta:
        verbose_name = 'покупка'
        verbose_name_plural = 'Список покупок'
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'recipe'),
                name='unique_user_purchase'
            ),
        )

    def __str__(self):
        # return self.recipe.name
        return (f'Рецепт "{self.recipe.name}" в списке в покупках'
                f' у пользователя "{self.user.username}"')
