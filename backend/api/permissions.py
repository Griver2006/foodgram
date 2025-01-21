from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsAuthorOrReadOnly(BasePermission):
    """
    Разрешение для авторов на редактирование рецепта,
    остальные могут только читать.
    """

    def has_object_permission(self, request, view, obj):
        return (request.method in SAFE_METHODS or request.user
                and (
                    obj.author == request.user
                    or (
                        request.user.is_authenticated
                        and request.user.is_staff
                    )
                ))
