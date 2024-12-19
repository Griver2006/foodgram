from django.urls import path, include
from django.contrib.auth import get_user_model

from rest_framework.routers import DefaultRouter

from api.views import (IngredientViewSet,
                       RecipeViewSet,
                       TagViewSet,
                       UsUserViewSet)


router = DefaultRouter()
router.register('users', UsUserViewSet)
router.register('recipes', RecipeViewSet, basename='recipes')
router.register('ingredients', IngredientViewSet)
router.register('tags', TagViewSet, basename='tags')

User = get_user_model()


urlpatterns = [
    path(
        'auth/',
        include('djoser.urls.authtoken')
    ),
    path(
        '', include(router.urls)
    )
]
