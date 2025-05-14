import base64
import datetime as dt
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from meals.models import Ingredient, Tag, Recipe, RecipeIngredient, Favorite, ShoppingCart
from users.models import User, Subscription


class Base64ImageField(serializers.ImageField):
    """Кастомное поле для обработки изображений в формате base64."""

    def to_internal_value(self, data):
        """."""
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]

            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    """."""

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient.id'
    )
    name = serializers.CharField(
        source='ingredient.name',
        read_only=True
    )
    unit = serializers.CharField(
        source='ingredient.unit',
        read_only=True
    )

    class Meta:
        """."""

        model = RecipeIngredient
        fields = ('id', 'name', 'unit', 'amount')


class IngredientSerializer(serializers.ModelSerializer):
    """."""

    class Meta:
        """."""

        model = Ingredient
        fields = ('id', 'name', 'unit')


class TagSerializer(serializers.ModelSerializer):
    """."""

    class Meta:
        """."""

        model = Tag
        fields = ('id', 'name', 'slug')


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    """."""

    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        """."""

        model = Recipe
        fields = ('id', 'name', 'image', 'cook_time')

    def get_image(self, obj):
        """."""
        return obj.image.url if obj.image else None


class RecipeSerializer(serializers.ModelSerializer):
    """."""

    ingredients = IngredientSerializer(many=True)

    class Meta:
        """."""

        model = Recipe
        fields = ('title',)


class UserSerializer(serializers.ModelSerializer):
    """."""

    is_subscribed = serializers.SerializerMethodField()
    profile_image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        """."""

        model = User
        fields = (
            'id', 'email', 'username', 'first_name',
            'last_name', 'is_subscribed', 'profile_image'
        )

    def get_is_subscribed(self, obj):
        """."""
        user = self.context['request'].user
        return (
            user.is_authenticated and Subscription.objects.filter(
                user=user, author=obj
            ).exists()
        )

    def get_profile_image(self, obj):
        """."""
        return obj.profile_image.url if obj.profile_image else None


class UserWithRecipesSerializer(UserSerializer):
    """."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        """."""

        fields = UserSerializer.Meta.fields + ('recipes', 'recipes_count')

    def get_recipes(self, obj):
        """."""
        request = self.context['request']
        recipes_limit = request.query_params.get('recipes_limit')
        queryset = obj.recipes.all()
        if recipes_limit:
            queryset = queryset[:int(recipes_limit)]
        return RecipeMinifiedSerializer(queryset, many=True).data

    def get_recipes_count(self, obj):
        """."""
        return obj.recipes.count()


class RecipeSerializer(serializers.ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    author = UserSerializer(read_only=True)
    ingredients = IngredientInRecipeSerializer(
        many=True,
        source='recipe_ingredients'
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField()

    class Meta:
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time'
        )

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        return (
            user.is_authenticated and
            Favorite.objects.filter(user=user, recipe=obj).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        return (
            user.is_authenticated and
            ShoppingCart.objects.filter(user=user, recipe=obj).exists()
        )

    def validate(self, data):
        # Валидация тегов и ингредиентов
        tags = self.initial_data.get('tags')
        ingredients = self.initial_data.get('ingredients')

        if not tags:
            raise ValidationError({'tags': 'Нужно выбрать хотя бы один тег'})
        if not ingredients:
            raise ValidationError(
                {'ingredients': 'Нужно выбрать хотя бы один ингредиент'}
            )

        return data

    def create_ingredients(self, recipe, ingredients):
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=recipe,
                ingredient=ingredient['ingredient']['id'],
                amount=ingredient['amount']
            ) for ingredient in ingredients
        ])

    def create(self, validated_data):
        ingredients = validated_data.pop('recipe_ingredients')
        tags = self.initial_data.get('tags')
        recipe = Recipe.objects.create(
            **validated_data,
            author=self.context['request'].user
        )
        recipe.tags.set(tags)
        self.create_ingredients(recipe, ingredients)
        return recipe

    def update(self, instance, validated_data):
        ingredients = validated_data.pop('recipe_ingredients', None)
        tags = self.initial_data.get('tags')
        
        instance = super().update(instance, validated_data)
        
        if tags is not None:
            instance.tags.set(tags)
        if ingredients is not None:
            instance.ingredients.clear()
            self.create_ingredients(instance, ingredients)
            
        return instance


class SubscriptionSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source='author.email', read_only=True)
    id = serializers.IntegerField(source='author.id', read_only=True)
    username = serializers.CharField(source='author.username', read_only=True)
    first_name = serializers.CharField(
        source='author.first_name',
        read_only=True
    )
    last_name = serializers.CharField(
        source='author.last_name',
        read_only=True
    )
    is_subscribed = serializers.SerializerMethodField()
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()
    profile_image = Base64ImageField()

    class Meta:
        model = Subscription
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'recipes', 'recipes_count', 'avatar'
        )

    def get_is_subscribed(self, obj):
        return True

    def get_recipes(self, obj):
        request = self.context.get('request')
        limit = request.query_params.get('recipes_limit')
        recipes = obj.author.recipes.all()
        if limit:
            recipes = recipes[:int(limit)]
        return RecipeMinifiedSerializer(recipes, many=True).data

    def get_recipes_count(self, obj):
        return obj.author.recipes.count()

    def get_profile_image(self, obj):
        author = obj.author
        return author.profile_image.url if author.profile_image else None


class SetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(required=True)
    current_password = serializers.CharField(required=True)
