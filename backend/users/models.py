from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError

from api.constants import (
    MAX_FIRST_NAME_CHAR_LENGTH,
    MAX_LAST_NAME_CHAR_LENGTH,
    STR_OUTPUT_SLICE
)


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
    first_name = models.CharField(
        max_length=MAX_FIRST_NAME_CHAR_LENGTH,
    )
    last_name = models.CharField(
        max_length=MAX_LAST_NAME_CHAR_LENGTH,
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


class Subscription(models.Model):
    """Связующая модель для подписок пользователей друг на друга."""

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Пользователь',
        related_name='user_subscriptions'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subscriptions_to_author',
        verbose_name='Автор'
    )

    class Meta:
        verbose_name = 'подписка'
        verbose_name_plural = 'Подписки'
        constraints = (
            models.UniqueConstraint(
                fields=('user', 'author'),
                name='unique_user_author'
            ),
        )

    def clean(self):
        if self.user == self.author:
            raise ValidationError(
                'Пользователь не может подписаться сам на себя.'
            )

    def save(self, *args, **kwargs):
        self.clean()
        super(Subscription, self).save(*args, **kwargs)

    def __str__(self):
        return self.author.username[:STR_OUTPUT_SLICE]
