from django.contrib.auth.models import AbstractUser
from django.db import models


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
        through='recipes.Follow',
        symmetrical=False,
        verbose_name='Подписки'
    )
    favourite_recipes = models.ManyToManyField(
        'recipes.Recipe',
        through='recipes.FavouriteRecipe',
        verbose_name='Избранное'
    )

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)
