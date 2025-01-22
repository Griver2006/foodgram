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

    @admin.display(description='Количество рецептов')
    def recipes_count(self, obj):
        return obj.recipes.count()

    @admin.display(description='Количество подписчиков')
    def subscriptions_count(self, obj):
        return Subscription.objects.filter(recipes_author=obj).count()


admin.site.register(Subscription)
