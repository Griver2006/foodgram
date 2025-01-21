from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth import get_user_model

from users.models import Subscription


User = get_user_model()


@admin.register(User)
class UserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Аватар', {'fields': ('avatar',)}),
    )
    list_display = (
        'username',
        'email',
        'is_staff',
        'recipes_count',
        'subscriptions_count'
    )
    search_fields = (
        'email',
        'username'
    )

    def recipes_count(self, obj):
        return obj.recipes.count()

    recipes_count.short_description = 'Количество рецептов'

    def subscriptions_count(self, obj):
        return Subscription.objects.filter(recipes_author=obj).count()

    subscriptions_count.short_description = 'Количество подписчиков'


admin.site.register(Subscription)
