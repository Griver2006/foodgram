from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Sum

from django_filters.rest_framework import DjangoFilterBackend

from rest_framework.views import APIView
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status, filters
from rest_framework.mixins import ListModelMixin, RetrieveModelMixin
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from djoser.views import UserViewSet

from api.filters import RecipeFilter
from api.models import (Follow,
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


class UsUserViewSet(UserViewSet):
    """
    Вьюсет для модели User, наследуется от стандартного вьюсета из djoser.
    """

    @action(detail=True, methods=('put', 'delete'))
    def avatar(self, request, id):
        user = request.user

        if request.method == 'PUT':
            serializer = UserSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {'avatar': request.build_absolute_uri(user.avatar.url)},
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    {'avatar': 'Обязательное поле.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        elif request.method == 'DELETE':
            user.avatar = 'users/avatar-icon.png'
            user.save()
            return Response({'detail': 'Аватар успешно удалён'}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'])
    def subscriptions(self, request):
        user = request.user
        following_users = User.objects.filter(followers__user=user)
        page = self.paginate_queryset(following_users)
        serializer = SubscriptionsSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(detail=True, methods=('post', 'delete'))
    def subscribe(self, request, id):
        followed = get_object_or_404(User, id=id)
        # try:
        #     followed = User.objects.get(id=id)
        # except ObjectDoesNotExist:
        #     return Response(
        #         data={
        #             'detail': 'Пользователь не найден'
        #         },
        #         status=status.HTTP_404_NOT_FOUND
        #     )

        if request.method == 'POST':
            try:
                Follow.objects.create(
                    user=request.user, following=followed
                )
            except ValidationError as e:
                return Response(
                    data={
                        'detail': e
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            except IntegrityError:
                return Response(
                    data={
                        'detail': 'Вы уже подписаны на данного пользователя'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            return Response(
                data=SubscriptionsSerializer(
                    followed, many=False, context={'request': request}
                ).data,
                status=status.HTTP_201_CREATED
            )
        elif request.method == 'DELETE':
            try:
                follow = Follow.objects.get(
                    user=request.user, following=followed
                )
            except ObjectDoesNotExist:
                return Response(
                    status=status.HTTP_400_BAD_REQUEST
                )
            follow.delete()
            return Response({'detail': 'Успешная отписка'},
                            status=status.HTTP_204_NO_CONTENT)


class TagViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    """
    Вьюсет для модели Tag.
    """

    pagination_class = None
    queryset = Tag.objects.all()
    serializer_class = TagSerializer


class ShortLinkRedirectView(APIView):
    """
    Вьюшка, которая производит редирект от короткой ссылки на нужный url.
    """

    def get(self, request, short_link):
        instance = get_object_or_404(Recipe, short_link=short_link)
        return redirect(f"/api/recipes/{instance.id}/")


class RecipeViewSet(ModelViewSet):
    """
    Вьюсет для модели Recipe.
    """

    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    filter_backends = (DjangoFilterBackend,)
    filterset_class = RecipeFilter

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk):
        """
        Функция, которая возвращает короткую ссылку рецепта из базы данных.
        """
        full_url = (f'{request.build_absolute_uri("/")}s/'
                    f'{get_object_or_404(Recipe, pk=pk).short_link}')

        return Response({'full_url': full_url})

    @action(detail=True, methods=('post', 'delete'))
    def shopping_cart(self, request, pk):
        """
        Функция для добавления рецепта в список покупок.
        """
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == 'POST':
            user = request.user

            if ShoppingList.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'detail': 'Рецепт уже добавлен в список покупок.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            ShoppingList.objects.create(user=user, recipe=recipe)

            return Response(
                RecipeShortSerializer(
                    recipe,
                    context={'request': request}
                ).data,
                status=status.HTTP_201_CREATED
            )

        elif request.method == 'DELETE':
            try:
                shopping_cart = ShoppingList.objects.get(
                    user=request.user, recipe=recipe
                )
            except ObjectDoesNotExist:
                return Response(
                    status=status.HTTP_400_BAD_REQUEST
                )
            shopping_cart.delete()

            return Response(
                {'detail': 'Рецепт успешно убран из списка покупок.'},
                status=status.HTTP_204_NO_CONTENT
            )

    @action(detail=False, methods=('get',))
    def download_shopping_cart(self, request):
        """
        Функция генерирует и возвращает текстовый файл, где перечисляются рецепты и суммируются все ингредиенты.
        """

        shopping_cart = ShoppingList.objects.filter(user=request.user).select_related('recipe')
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

        response = HttpResponse(content, content_type='text/plain; charset=utf-8')
        response['Content-Disposition'] = 'attachment; filename="shopping_list.txt"'

        return response

    @action(detail=True, methods=('delete', 'post'))
    def favorite(self, request, pk):
        """
        Функция для добавления рецепта в список избранных.
        """
        recipe = get_object_or_404(Recipe, pk=pk)

        if request.method == 'POST':
            user = request.user

            if FavouriteRecipe.objects.filter(user=user, recipe=recipe).exists():
                return Response(
                    {'detail': 'Рецепт уже добавлен есть в избранном.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            FavouriteRecipe.objects.create(user=user, recipe=recipe)

            return Response(
                RecipeShortSerializer(
                    recipe,
                    context={'request': request}
                ).data,
                status=status.HTTP_201_CREATED
            )
        elif request.method == 'DELETE':
            try:
                favourite_recipe = FavouriteRecipe.objects.get(
                    user=request.user, recipe=recipe
                )
            except ObjectDoesNotExist:
                return Response(
                    status=status.HTTP_400_BAD_REQUEST
                )
            favourite_recipe.delete()
            return Response(
                {'detail': 'Рецепт успешно убран из избранных.'},
                status=status.HTTP_204_NO_CONTENT)


class IngredientViewSet(ListModelMixin, RetrieveModelMixin, GenericViewSet):
    """
    Вьюсет для модели Ingredient.
    """

    pagination_class = None
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = (filters.SearchFilter,)
    search_fields = ('name', )






