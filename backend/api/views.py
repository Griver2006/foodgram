from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import IntegrityError
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Sum

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from djoser.views import UserViewSet

from api.filters import IngredientFilter, RecipeFilter
from api.permissions import IsAuthorOrReadOnly
from recipes.models import (Follow,
                            FavouriteRecipe,
                            Ingredient,
                            Recipe,
                            RecipeIngredient,
                            ShoppingList,
                            Tag,
                            User)

from api.serializers import (IngredientSerializer,
                             RecipeSerializer,
                             RecipeShortSerializer,
                             SubscriptionsSerializer,
                             TagSerializer,
                             UserSerializer)


def handle_add_remove(request, model, filter_kwargs, serializer=None):
    """
    Вспомогательная функция для добавления и удаления объектов.
    """
    if request.method == 'POST':
        try:
            model.objects.create(**filter_kwargs)
        except IntegrityError:
            return Response(
                {'detail': 'Объект уже существует.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            serializer.data if serializer
            else {'detail': 'Успешно добавлено.'},
            status=status.HTTP_201_CREATED
        )
    elif request.method == 'DELETE':
        instance = model.objects.filter(**filter_kwargs).first()
        if not instance:
            return Response(
                {'detail': 'Объект не найден.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        instance.delete()
        return Response(
            {'detail': 'Успешно удалено.'},
            status=status.HTTP_204_NO_CONTENT
        )


class UsUserViewSet(UserViewSet):
    """
    Вьюсет для модели User, наследуется от стандартного вьюсета из djoser.
    """

    @action(
        detail=True,
        methods=('put', 'delete'),
        permission_classes=(permissions.IsAuthenticated,)
    )
    def avatar(self, request, id):
        user = request.user
        if request.method == 'PUT':
            if len(request.data) != 1:
                return Response(
                    {'detail': 'Нужно передать только avatar'},
                    status.HTTP_400_BAD_REQUEST
                )
            elif 'avatar' not in request.data:
                return Response(
                    {'avatar': 'Поле обязательное'},
                    status.HTTP_400_BAD_REQUEST
                )
            serializer = UserSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {'avatar': request.build_absolute_uri(user.avatar.url)},
                    status=status.HTTP_200_OK
                )
        elif request.method == 'DELETE':
            user.avatar = ''
            user.save()
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
        following_users = User.objects.filter(followers__user=request.user)
        page = self.paginate_queryset(following_users)
        serializer = SubscriptionsSerializer(
            page, many=True, context={'request': request}
        )
        return self.get_paginated_response(serializer.data)

    @action(
        detail=True,
        methods=('post', 'delete'),
        permission_classes=(permissions.IsAuthenticated,)
    )
    def subscribe(self, request, id):
        if request.user.id == int(id):
            return Response(
                {'detail': 'Пользователь не может '
                           'подписаться/отписаться сам на себя.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        followed = get_object_or_404(User, id=id)
        return handle_add_remove(
            request,
            Follow,
            filter_kwargs={'user': request.user, 'following': followed},
            serializer=SubscriptionsSerializer(
                followed, context={'request': request}
            ) if request.method == 'POST' else None
        )

    @action(
        detail=False,
        methods=('get', 'put', 'patch', 'delete'),
        permission_classes=(permissions.IsAuthenticated,)
    )
    def me(self, request, *args, **kwargs):
        self.get_object = self.get_instance
        if request.method == 'GET':
            return self.retrieve(request, *args, **kwargs)
        elif request.method == 'PUT':
            return self.update(request, *args, **kwargs)
        elif request.method == 'PATCH':
            return self.partial_update(request, *args, **kwargs)
        elif request.method == 'DELETE':
            return self.destroy(request, *args, **kwargs)


class TagViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    """
    Вьюсет для модели Tag.
    """
    pagination_class = None
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = (permissions.AllowAny, )


def redirect_to_recipe(request, short_link):
    """
    Вьюшка, которая производит редирект от короткой ссылки на нужный url.
    """

    recipe = get_object_or_404(Recipe, short_link=short_link)
    # Перенаправляем на страницу рецепта
    return redirect(f'/recipes/{recipe.id}/')


class RecipeViewSet(ModelViewSet):
    """
    Вьюсет для модели Recipe.
    """

    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    filter_backends = (
        DjangoFilterBackend,
    )
    permission_classes = (
        permissions.IsAuthenticatedOrReadOnly,
        IsAuthorOrReadOnly
    )
    filterset_class = RecipeFilter

    def perform_create(self, serializer):
        try:
            serializer.save(author=self.request.user)
        except ObjectDoesNotExist as e:
            return Response({'detail': e}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk):
        full_url = (f'{request.build_absolute_uri("/")}s/'
                    f'{get_object_or_404(Recipe, pk=pk).short_link}')

        return Response({'short-link': full_url})

    @action(detail=True, methods=('post', 'delete'))
    def shopping_cart(self, request, pk):
        recipe = get_object_or_404(Recipe, pk=pk)
        return handle_add_remove(
            request,
            ShoppingList,
            filter_kwargs={'user': request.user, 'recipe': recipe},
            serializer=RecipeShortSerializer(
                recipe, context={'request': request}
            ) if request.method == 'POST' else None
        )

    @action(
        detail=False,
        methods=('get',),
        permission_classes=(permissions.IsAuthenticated,)
    )
    def download_shopping_cart(self, request):
        shopping_cart = ShoppingList.objects.filter(
            user=request.user
        ).select_related('recipe')
        recipes = shopping_cart.values('recipe__name', 'recipe__cooking_time')

        total_ingredients = RecipeIngredient.objects.filter(
            recipe__in=shopping_cart.values_list('recipe', flat=True)
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(total_amount=Sum('amount')).order_by('ingredient__name')

        content = ''

        for recipe in recipes:
            content += (
                f'Название: {recipe["recipe__name"]}\n'
                f'Время приготовления: {recipe["recipe__cooking_time"]}\n\n'
            )

        content += 'Список всех ингредиентов:\n'

        for item in total_ingredients:
            content += (
                f'  - {item["ingredient__name"]} '
                f'({item["ingredient__measurement_unit"]}) — '
                f'{item["total_amount"]}\n'
            )

        response = HttpResponse(
            content, content_type='text/plain; charset=utf-8'
        )
        response['Content-Disposition'] = ('attachment; '
                                           'filename="shopping_list.txt"')

        return response

    @action(detail=True, methods=('delete', 'post'))
    def favorite(self, request, pk):
        recipe = get_object_or_404(Recipe, pk=pk)

        return handle_add_remove(
            request,
            FavouriteRecipe,
            filter_kwargs={'user': request.user, 'recipe': recipe},
            serializer=RecipeShortSerializer(
                recipe, context={'request': request}
            ) if request.method == 'POST' else None
        )


class IngredientViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    """
    Вьюсет для модели Ingredient.
    """

    pagination_class = None
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = (permissions.AllowAny, )
    filter_backends = (DjangoFilterBackend,)
    filterset_class = IngredientFilter
