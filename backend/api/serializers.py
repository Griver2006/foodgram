from drf_extra_fields.fields import Base64ImageField
from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from djoser.serializers import UserSerializer as BaseUserSerializer

from recipes.models import (FavouriteRecipe,
                            Ingredient,
                            Recipe,
                            RecipeIngredient,
                            ShoppingList,
                            Tag)
from users.models import Subscription


User = get_user_model()


class UserSerializer(BaseUserSerializer):
    """
    Сериализатор для кастомной модели User.
    """

    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(required=True)

    class Meta(BaseUserSerializer.Meta):
        model = User
        fields = BaseUserSerializer.Meta.fields + (
            'is_subscribed',
            'avatar'
        )

    def validate(self, data):
        # Проверка только для PUT
        request = self.context['request']
        if request and request.method == 'PUT':
            if len(data) != 1:
                raise serializers.ValidationError(
                    {'detail': 'Нужно передать только avatar'}
                )

        return data

    def validate_avatar(self, value):
        # Проверка на обязательность avatar только для PUT
        request = self.context['request']
        if request and request.method == 'PUT' and not value:
            raise serializers.ValidationError(
                'Поле avatar должно быть заполнено'
            )

        return value

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return obj.subscriptions_to_author.filter(user=user).exists()

        return False


class TagSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Tag.
    """

    class Meta:
        model = Tag
        fields = (
            'id',
            'name',
            'slug'
        )


class IngredientSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Ingredient.
    """

    class Meta:
        model = Ingredient
        fields = (
            'id',
            'name',
            'measurement_unit'
        )


class RecipeIngredientReadSerializer(serializers.ModelSerializer):
    """
    Сериализатор для записи данных(ингредиентов) в модель RecipeIngredient.
    Нужен как поле для сериализатора RecipeReadSerializer.
    """

    id = serializers.IntegerField(
        source='ingredient.id',
        read_only=True
    )
    name = serializers.CharField(
        source='ingredient.name',
        required=False,
        read_only=True
    )
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit',
        read_only=True
    )
    amount = serializers.IntegerField(
        read_only=True
    )

    class Meta:
        model = RecipeIngredient
        fields = (
            'id',
            'name',
            'measurement_unit',
            'amount'
        )


class RecipeIngredientWriteSerializer(serializers.Serializer):
    """
    Сериализатор для записи данных(ингредиентов) в модель RecipeIngredient.
    Нужен как поле для сериализатора RecipeWriteSerializer.
    """

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient'
    )
    amount = serializers.IntegerField(
        min_value=1,
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'amount')


class BaseRecipeSerializer(serializers.ModelSerializer):
    """
    Базовый сериализатор для модели Recipe.
    """

    author = UserSerializer(
        read_only=True
    )
    is_favorited = serializers.BooleanField(read_only=True)
    is_in_shopping_cart = serializers.BooleanField(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'name',
            'image',
            'text',
            'cooking_time'
        )


class RecipeReadSerializer(BaseRecipeSerializer):
    """
    Сериализатор для получения данных(рецептов) из модели Recipe.
    """
    tags = TagSerializer(
        many=True,
        read_only=True
    )
    ingredients = RecipeIngredientReadSerializer(
        source='recipe_ingredients',
        many=True,
        read_only=True
    )

    class Meta(BaseRecipeSerializer.Meta):
        pass


class RecipeWriteSerializer(BaseRecipeSerializer):
    """
    Сериализатор для записи данных(рецептов) в модель Recipe.
    """

    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
    )
    ingredients = RecipeIngredientWriteSerializer(
        many=True,
        source='recipe_ingredients'
    )
    image = Base64ImageField()

    class Meta(BaseRecipeSerializer.Meta):
        pass

    def to_representation(self, instance):
        user = self.context['request'].user

        # Пересчитываем значения для аутентифицированных пользователей
        instance.is_favorited = (
            FavouriteRecipe.objects.filter(
                user=user, recipe=instance
            ).exists()
            if user.is_authenticated else False
        )
        instance.is_in_shopping_cart = (
            ShoppingList.objects.filter(user=user, recipe=instance).exists()
            if user.is_authenticated else False
        )

        representation = super().to_representation(instance)
        representation['tags'] = TagSerializer(
            instance.tags.all(), many=True
        ).data
        representation['ingredients'] = RecipeIngredientReadSerializer(
            instance.recipe_ingredients.all(), many=True
        ).data

        return representation

    def validate_image(self, value):
        if not value:
            raise serializers.ValidationError(
                'Поле image должно быть заполнено'
            )

        return value

    def _save_ingredients(self, recipe, ingredients_data):
        """
        Метод для сохранения ингредиентов.
        Также сохраняет и количество ингредиента.
        """
        recipe.recipe_ingredients.all().delete()
        recipe_ingredients = [
            RecipeIngredient(
                recipe=recipe,
                ingredient=ingredient_data['ingredient'],
                amount=ingredient_data['amount']
            )
            for ingredient_data in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(recipe_ingredients)

    def create(self, validated_data):
        tags = validated_data.pop('tags', [])
        ingredients_data = validated_data.pop('recipe_ingredients', [])

        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self._save_ingredients(recipe, ingredients_data)

        return recipe

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', [])
        ingredients_data = validated_data.pop('recipe_ingredients', [])

        instance = super().update(instance, validated_data)

        instance.tags.set(tags)
        self._save_ingredients(instance, ingredients_data)

        return instance

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError('Должен быть хотя бы 1 тег.')

        # Проверка на повторения тегов
        if len(set(value)) != len(value):
            raise serializers.ValidationError('Теги не должны повторяться.')

        return value

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                'Должен быть хотя бы 1 ингредиент.'
            )

        # Проверка на повторения ингредиентов
        ingredient_ids = [item['ingredient'].id for item in value]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                'Ингредиенты не должны повторяться.'
            )

        return value


class RecipeShortSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Recipe, но используются не все поля.
    """

    image = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Recipe
        fields = (
            'id',
            'name',
            'image',
            'cooking_time'
        )

    def get_image(self, obj):
        if obj.image:
            return self.context['request'].build_absolute_uri(obj.image.url)

        return None


class BaseFavouriteAndShoppingListSerializer(serializers.ModelSerializer):
    """
    Базовый класс для Избранного и Списка покупок.
    """
    recipe = serializers.PrimaryKeyRelatedField(
        queryset=Recipe.objects.only('id', 'name', 'image', 'cooking_time'),
    )

    class Meta:
        fields = (
            'user',
            'recipe'
        )

    def to_representation(self, instance):
        return RecipeShortSerializer(
            instance.recipe,
            context={'request': self.context['request']}
        ).to_representation(instance.recipe)

    def validate(self, data):
        recipe = data['recipe']

        if self.Meta.model.objects.filter(
                user=data['user'], recipe=recipe
        ).exists():
            raise ValidationError(
                {'detail': 'Запись уже есть в базе'}
            )

        return data


class FavouriteSerializer(BaseFavouriteAndShoppingListSerializer):
    class Meta(BaseFavouriteAndShoppingListSerializer.Meta):
        model = FavouriteRecipe


class ShoppingListSerializer(BaseFavouriteAndShoppingListSerializer):
    class Meta(BaseFavouriteAndShoppingListSerializer.Meta):
        model = ShoppingList


class SubscriptionsReadSerializer(UserSerializer):
    """
    Сериализатор для модели, которая связывает Follow и User, подписка короче.
    """

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.IntegerField(default=0, read_only=True)

    class Meta(UserSerializer.Meta):
        model = User
        fields = UserSerializer.Meta.fields + (
            'recipes',
            'recipes_count'
        )

    def get_recipes(self, obj):
        request = self.context['request']
        recipes = obj.recipes.all()
        recipes_limit = request.query_params.get('recipes_limit')
        if recipes_limit:
            try:
                recipes = recipes[:int(recipes_limit)]
            except ValueError:
                pass

        return RecipeShortSerializer(
            recipes, many=True, context={'request': request}
        ).data


class SubscriptionsWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subscription
        fields = (
            'user',
            'author'
        )

    def validate(self, data):
        user = self.context['request'].user
        author = data['author']

        if user == author:
            raise ValidationError(
                {'author': 'Вы не можете подписаться на себя.'}
            )
        if author.subscriptions_to_author.filter(user=user).exists():
            raise ValidationError(
                {'author': 'Вы уже подписаны на этого пользователя.'}
            )

        return data

    def to_representation(self, instance):
        return SubscriptionsReadSerializer(
            instance.author,
            context={'request': self.context['request']}
        ).to_representation(instance.author)
