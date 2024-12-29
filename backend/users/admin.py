from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm

from django.contrib.auth import get_user_model


User = get_user_model()


class UserChangeFormWithSpecialFields(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User


@admin.register(User)
class UserAdmin(UserAdmin):
    form = UserChangeFormWithSpecialFields
    fieldsets = UserAdmin.fieldsets + (
        ('Аватар', {'fields': ('avatar',)}),
    )
    list_display = ('username', 'email', 'is_staff')
    search_fields = ('email', 'username')
