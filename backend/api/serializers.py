import base64

from hashids import Hashids

from djoser.serializers import UserCreateSerializer

from django.core.files.base import ContentFile
from django.contrib.auth import get_user_model
from rest_framework import serializers


from recipes.models import (Follow,
                            FavouriteRecipe,
                            Ingredient,
                            Recipe,
                            RecipeIngredient,
                            ShoppingList,
                            Tag)


User = get_user_model()
hashids = Hashids(min_length=3)


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]

            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class UsUserCreateSerializer(UserCreateSerializer):
    """
    Сериализатор для регистрации пользователя с переопределёнными полями.
    """
    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=True)

    class Meta(UserCreateSerializer.Meta):
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'password'
        )


class UserSerializer(serializers.ModelSerializer):
    """
    Сериализатор для кастомной модели User.
    """

    is_subscribed = serializers.SerializerMethodField()
    avatar = Base64ImageField(required=True)

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar'
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Follow.objects.filter(
                user=request.user, following=obj
            ).exists()
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


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели, которая связывает Recipe и Ingredient.
    """

    id = serializers.IntegerField(source='ingredient.id')
    name = serializers.CharField(source='ingredient.name', required=False)
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Recipe.
    """

    tags = serializers.PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True,
    )
    ingredients = RecipeIngredientSerializer(
        many=True,
        source='recipe_ingredients',
    )
    author = UserSerializer(
        read_only=True
    )
    image = Base64ImageField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()

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

    def validate(self, data):
        """Валидация обязательных полей при обновлении."""
        request_method = self.context['request'].method
        if request_method == 'PATCH':
            required_fields = [
                'tags', 'recipe_ingredients', 'name', 'text', 'cooking_time'
            ]
            missing_fields = [field
                              for field in required_fields
                              if field not in data]
            if 'recipe_ingredients' in missing_fields:
                missing_fields.remove('recipe_ingredients')
                missing_fields.append('ingredients')

            if missing_fields:
                raise serializers.ValidationError({
                    field: 'Это поле обязательно для заполнения.'
                    for field in missing_fields
                })
        return data

    def validate_cooking_time(self, value):
        if value < 1:
            raise serializers.ValidationError(
                'Значение приготовления не может быть меньше 1.'
            )
        return value

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError('Должен быть хотя бы 1 тег.')
        if len(set(value)) != len(value):
            raise serializers.ValidationError('Теги не должны повторяться.')

        return value

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError(
                'Должен быть хотя бы 1 ингредиент.'
            )

        # Проверка на повторения ингредиентов
        ingredient_ids = [item['ingredient']['id']
                          for item in value if 'ingredient' in item]
        if len(ingredient_ids) != len(set(ingredient_ids)):
            raise serializers.ValidationError(
                'Ингредиенты не должны повторяться.'
            )

        # Проверка на отсутствие ингредиентов в базе
        existing_ingredients = Ingredient.objects.filter(
            id__in=ingredient_ids
        ).values_list('id', flat=True)
        missing_ingredients = set(ingredient_ids) - set(existing_ingredients)
        if missing_ingredients:
            raise serializers.ValidationError(
                'Следующие ингредиенты отсутствуют в базе данных: '
                + ', '.join(map(str, missing_ingredients))
            )

        # Проверка на правильную заполненность каждого из ингредиентов
        missing_fields = []
        for item in value:
            if 'ingredient' not in item:
                missing_fields.append('id')
            if 'amount' not in item:
                missing_fields.append('amount')
            if item['amount'] < 1:
                raise serializers.ValidationError(
                    {'amount': 'Количество не может быть меньше 1.'}
                )
        if missing_fields:
            raise serializers.ValidationError({
                field: 'Это поле обязательно для заполнения.'
                for field in missing_fields
            })

        return value

    def _save_ingredients(self, recipe, ingredients_data):
        """
        Функция для сохранения ингредиентов.
        Также сохраняет и количество ингредиента.
        """
        recipe.recipe_ingredients.all().delete()
        recipe_ingredients = [
            RecipeIngredient(
                recipe=recipe,
                ingredient=Ingredient.objects.get(
                    id=ingredient_data['ingredient']['id']
                ),
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

        recipe.short_link = hashids.encode(recipe.pk)
        recipe.save()

        return recipe

    def update(self, instance, validated_data):
        tags = validated_data.pop('tags', [])
        ingredients_data = validated_data.pop('recipe_ingredients', [])

        instance = super().update(instance, validated_data)

        instance.tags.set(tags)
        self._save_ingredients(instance, ingredients_data)
        instance.save()

        return instance

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['tags'] = TagSerializer(
            instance.tags.all(), many=True
        ).data
        return representation

    def get_is_favorited(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return FavouriteRecipe.objects.filter(
                user=user, recipe=obj
            ).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        user = self.context.get('request').user
        if user.is_authenticated:
            return ShoppingList.objects.filter(user=user, recipe=obj).exists()
        return False


class RecipeShortSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Recipe, но используются не все поля.
    """

    image = serializers.SerializerMethodField()

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
            return self.context.get(
                'request'
            ).build_absolute_uri(obj.image.url)
        return None


class SubscriptionsSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели, которая связывает Follow и User, подписка короче.
    """

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'recipes',
            'recipes_count',
            'avatar'
        )

    def get_recipes(self, obj):
        request = self.context.get('request')
        recipes_limit = request.query_params.get('recipes_limit')
        if recipes_limit and recipes_limit.isdigit():
            recipes = obj.recipes.all()[:int(recipes_limit)]
        else:
            recipes = obj.recipes.all()

        return RecipeShortSerializer(
            recipes, many=True, context={'request': request}
        ).data

    def get_recipes_count(self, obj):
        return obj.recipes.count()

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Follow.objects.filter(
                user=request.user, following=obj
            ).exists()
        return False
