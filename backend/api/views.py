from django.http import FileResponse
from django.shortcuts import get_object_or_404
from django.db.models import Sum, OuterRef, Exists, Count
from rest_framework.reverse import reverse
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from djoser.views import UserViewSet as BaseUserViewSet
from django_filters.rest_framework import DjangoFilterBackend

from recipes.models import (FavouriteRecipe,
                            Ingredient,
                            Recipe,
                            RecipeIngredient,
                            ShoppingList,
                            Tag,
                            User)
from users.models import Subscription
from api.filters import IngredientFilter, RecipeFilter
from api.permissions import IsAuthorOrReadOnly
from api.serializers import (AvatarSerializer,
                             FavouriteSerializer,
                             IngredientSerializer,
                             RecipeReadSerializer,
                             RecipeWriteSerializer,
                             ShoppingListSerializer,
                             SubscriptionsReadSerializer,
                             SubscriptionsWriteSerializer,
                             TagSerializer,
                             UserSerializer)
from api.shopping_cart import get_shopping_cart_file_buffer


class UserViewSet(BaseUserViewSet):
    """
    Вьюсет для модели User, наследуется от стандартного вьюсета из djoser.
    """

    @action(
        detail=True,
        methods=('put',),
        permission_classes=(permissions.IsAuthenticated,)
    )
    def avatar(self, request, id):
        user = request.user
        serializer = AvatarSerializer(
            user,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {'avatar': request.build_absolute_uri(user.avatar.url)},
            status=status.HTTP_200_OK
        )

    @avatar.mapping.delete
    def delete_avatar(self, request, id):
        user = request.user
        user.avatar.delete()

        return Response(
            {'avatar': 'Аватар успешно удалён'},
            status=status.HTTP_204_NO_CONTENT
        )

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(permissions.IsAuthenticated,)
    )
    def subscriptions(self, request):
        subscriptions = User.objects.filter(
            subscriptions_to_author__user=request.user
        ).annotate(
            recipes_count=Count('recipes')
        ).order_by('username')
        page = self.paginate_queryset(subscriptions)
        serializer = SubscriptionsReadSerializer(
            page, many=True, context={'request': request}
        )

        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=('post',),
        permission_classes=(permissions.IsAuthenticated,)
    )
    def subscribe(self, request, id):
        author = get_object_or_404(User, id=id)

        serializer = SubscriptionsWriteSerializer(
            data={'user': request.user.id, 'author': author.id},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            data=serializer.data,
            status=status.HTTP_201_CREATED
        )

    @subscribe.mapping.delete
    def delete_subscribe(self, request, id):
        author = get_object_or_404(
            User,
            id=id,
        )
        subscription = Subscription.objects.filter(
            user=request.user, author__id=author.id
        ).delete()
        if subscription[0]:
            return Response(
                {'detail': 'Подписка удалена.'},
                status=status.HTTP_204_NO_CONTENT
            )
        else:
            return Response(
                {'detail': 'Подписка не найдена.'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(permissions.IsAuthenticated,)
    )
    def me(self, request):
        return Response(
            UserSerializer(
                request.user,
                context={'request': request}
            ).data
        )


class TagViewSet(ReadOnlyModelViewSet):
    """
    Вьюсет для модели Tag.
    """
    pagination_class = None
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (permissions.AllowAny, )


class RecipeViewSet(ModelViewSet):
    """
    Вьюсет для модели Recipe.
    """

    filter_backends = (
        DjangoFilterBackend,
    )
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly,
        IsAuthorOrReadOnly
    )
    filterset_class = RecipeFilter

    def get_queryset(self):
        user = self.request.user

        queryset = Recipe.objects.all().select_related(
            'author'
        ).prefetch_related('tags', 'ingredients')

        if user.is_authenticated:
            queryset = queryset.annotate(
                is_favorited=Exists(
                    FavouriteRecipe.objects.filter(
                        user=user, recipe=OuterRef('pk')
                    )
                ),
                is_in_shopping_cart=Exists(
                    ShoppingList.objects.filter(
                        user=user, recipe=OuterRef('pk')
                    )
                )
            )

        return queryset

    def get_serializer_class(self):
        if self.action in ('list', 'retrieve'):
            return RecipeReadSerializer
        return RecipeWriteSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=('get',), url_path='get-link')
    def get_link(self, request, pk):
        full_url = reverse(
            'redirect_to_recipe',
            args=(get_object_or_404(Recipe, pk=pk).short_link,),
            request=request
        )[:-1]

        return Response({'short-link': full_url})

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(permissions.IsAuthenticated,)
    )
    def download_shopping_cart(self, request):
        user = request.user

        recipes = user.purchases.select_related(
            'recipe'
        ).values(
            'recipe__name', 'recipe__cooking_time'
        )

        total_ingredients = RecipeIngredient.objects.filter(
            recipe__purchases__user=user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(total_amount=Sum('amount')).order_by('ingredient__name')

        response = FileResponse(
            get_shopping_cart_file_buffer(recipes, total_ingredients),
            as_attachment=True,
            filename='shopping_cart.txt',
            content_type='text/plain; charset=utf-8',
        )

        return response

    def add_in_favorite_or_in_shopping_list(self, serializer, pk):
        # В реьвю вы сказали сделать этот метод статиком методом
        # и доставать request из self, но если метод будет статичным
        # то self не передаётся, поэтому не сделал этот метод статичным
        recipe = get_object_or_404(Recipe, id=pk)
        request = self.request

        serializer = serializer(
            data={'user': request.user.id, 'recipe': recipe.pk},
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            data=serializer.data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=('post',))
    def favorite(self, request, pk):
        return self.add_in_favorite_or_in_shopping_list(
            FavouriteSerializer, pk
        )

    @action(detail=True, methods=('post',))
    def shopping_cart(self, request, pk):
        return self.add_in_favorite_or_in_shopping_list(
            ShoppingListSerializer, pk
        )

    @favorite.mapping.delete
    def delete_favorite(self, request, pk):
        recipe = get_object_or_404(Recipe, pk=pk)
        deleted_count, _ = FavouriteRecipe.objects.filter(
            user=request.user, recipe_id=recipe.pk
        ).delete()

        if deleted_count:
            return Response(
                {'detail': 'Успешно удалено.'},
                status=status.HTTP_204_NO_CONTENT
            )
        else:
            return Response(
                {'detail': 'Рецепта не было в избранном.'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk):
        recipe = get_object_or_404(Recipe, pk=pk)
        deleted_count, _ = ShoppingList.objects.filter(
            user=request.user, recipe_id=recipe.pk
        ).delete()

        if deleted_count:
            return Response(
                {'detail': 'Успешно удалено.'},
                status=status.HTTP_204_NO_CONTENT
            )
        else:
            return Response(
                {'detail': 'Рецепта не было в списке покупок.'},
                status=status.HTTP_400_BAD_REQUEST
            )


class IngredientViewSet(ReadOnlyModelViewSet):
    """
    Вьюсет для модели Ingredient.
    """

    pagination_class = None
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (permissions.AllowAny, )
    filter_backends = (DjangoFilterBackend, )
    filterset_class = IngredientFilter
