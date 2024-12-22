from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAuthorOrReadOnly(BasePermission):
    """
    Разрешение для авторов на редактирование рецепта,
    остальные могут только читать.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True

        return (
            request.user
            and (
                obj.author == request.user
                or (
                    request.user.is_authenticated
                    and request.user.is_staff
                )
            )
        )


class IsAdminOrReadOnly(BasePermission):
    """
    Разрешение только для администраторов или только для чтения.

    Позволяет выполнять безопасные HTTP методы всем пользователям,
    а остальные методы только администраторам.
    """

    def has_permission(self, request, view):
        """Проверяет, имеет ли пользователь разрешение."""
        if request.method in SAFE_METHODS:
            return True

        return (
            request.user
            and request.user.is_authenticated
            and request.user.is_staff
        )


class CurrentUserOrAdminOrReadOnly(BasePermission):
    """
    Разрешение для текущего пользователя, администратора
    или для чтения.
    """

    def has_object_permission(self, request, view, obj):
        user = request.user

        if request.method in SAFE_METHODS:
            return True

        return (
            user.is_authenticated
            and (
                isinstance(obj, type(user))
                and obj == user
                or user.is_staff
            )
        )
