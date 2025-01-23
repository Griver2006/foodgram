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
from api.constants import MIN_INGREDIENT_AMOUNT_QUANTITY


User = get_user_model()


class AvatarSerializer(serializers.ModelSerializer):
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ('avatar',)

    def to_representation(self, instance):
        if instance:
            return self.context['request'].build_absolute_uri(instance.url)

        return None

    def validate(self, value):
        avatar = value.get('avatar', False)
        # Проверка на заполненность поля avatar только для PUT, иначе ошибка
        if self.context['request'].method == 'PUT' and not avatar:
            raise serializers.ValidationError(
                {'avatar': 'Поле avatar должно быть заполнено'}
            )

        return value


class UserSerializer(BaseUserSerializer):
    """
    Сериализатор для кастомной модели User.
    """

    is_subscribed = serializers.SerializerMethodField()
    avatar = AvatarSerializer()

    class Meta(BaseUserSerializer.Meta):
        model = User
        fields = BaseUserSerializer.Meta.fields + (
            'is_subscribed',
            'avatar'
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request', False)

        return (
            request and request.user.is_authenticated
            and obj.subscriptions_to_author.filter(
                user=request.user
            ).exists()
        )


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
    )
    amount = serializers.IntegerField(
        min_value=MIN_INGREDIENT_AMOUNT_QUANTITY,
    )

    class Meta:
        model = RecipeIngredient
        fields = (
            'id',
            'amount'
        )


class RecipeReadSerializer(serializers.ModelSerializer):
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

    author = UserSerializer(
        read_only=True
    )
    is_favorited = serializers.BooleanField(
        default=False,
        read_only=True
    )
    is_in_shopping_cart = serializers.BooleanField(
        default=False,
        read_only=True
    )

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


class RecipeWriteSerializer(serializers.ModelSerializer):
    """
    Сериализатор для записи данных(рецептов) в модель Recipe.
    """

    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
    )
    ingredients = RecipeIngredientWriteSerializer(
        many=True,
    )
    author = UserSerializer(
        read_only=True
    )
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'tags',
            'author',
            'ingredients',
            'name',
            'image',
            'text',
            'cooking_time'
        )

    def to_representation(self, instance):
        return RecipeReadSerializer(
            instance,
            context=self.context
        ).data

    def _save_ingredients(self, recipe, ingredients_data):
        """
        Метод для сохранения ингредиентов.
        Также сохраняет и количество ингредиента.
        """
        recipe_ingredients = [
            RecipeIngredient(
                recipe=recipe,
                ingredient=ingredient_data['id'],
                amount=ingredient_data['amount']
            )
            for ingredient_data in ingredients_data
        ]
        RecipeIngredient.objects.bulk_create(recipe_ingredients)

    def create(self, validated_data):
        tags = validated_data.pop('tags', [])
        ingredients_data = validated_data.pop('ingredients', [])

        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self._save_ingredients(recipe, ingredients_data)

        return recipe

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', [])
        ingredients_data = validated_data.pop('ingredients', [])

        instance = super().update(instance, validated_data)

        instance.tags.set(tags)
        instance.recipe_ingredients.all().delete()
        self._save_ingredients(instance, ingredients_data)

        return instance

    def validate(self, data):
        # Проверяем присутствие всех обязательных полей
        request_method = self.context['request'].method
        if request_method == 'PATCH':
            required_fields = [
                'tags',
                'ingredients',
                'name',
                'text',
                'cooking_time',
            ]
            missing_fields = [field
                              for field in required_fields
                              if field not in data]

            if missing_fields:
                raise serializers.ValidationError({
                    field: 'Это поле обязательно для заполнения.'
                    for field in missing_fields
                })

        errors = {}

        # ВАЛИДИРУЕМ ТЕГИ
        tags = data['tags']
        if not tags:
            errors['tags'] = 'Должен быть хотя бы 1 тег.'

        # Проверка на повторения тегов
        if len(set(tags)) != len(tags):
            errors['tags'] = 'Теги не должны повторяться.'

        # ВАЛИДИРУЕМ ИНГРЕДИЕНТЫ
        ingredients = data['ingredients']
        if not ingredients:
            errors['ingredients'] = 'Должен быть хотя бы 1 ингредиент.'

        # Проверка на повторения ингредиентов
        ingredient_ids = [item['id'].id for item in ingredients]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            errors['ingredients'] = 'Ингредиенты не должны повторяться.'

        if errors:
            raise serializers.ValidationError(errors)

        return data

    def validate_image(self, value):
        if not value:
            raise serializers.ValidationError(
                'Поле не должно быть пустым'
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

    class Meta:
        fields = (
            'user',
            'recipe'
        )

    def to_representation(self, instance):
        return RecipeShortSerializer(
            instance.recipe,
            context=self.context
        ).data

    def validate(self, data):
        recipe = data['recipe']

        if self.Meta.model.objects.filter(
                user=data['user'], recipe=recipe
        ).exists():
            raise ValidationError(
                {
                    'detail': 'Рецепт уже '
                              'есть в '
                              + self.Meta.model._meta.verbose_name_plural
                }
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
            recipes,
            many=True,
            context=self.context
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
            context=self.context
        ).data
