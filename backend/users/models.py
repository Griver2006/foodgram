from django.contrib.auth.models import AbstractUser
from django.db import models

from api.constants import STR_OUTPUT_SLICE


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
    )

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('username',)

    def __str__(self):
        """Возвращает строковое представление пользователя."""
        return self.username[:STR_OUTPUT_SLICE]
