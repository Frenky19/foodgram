import base64
# import datetime as dt
from django.core.files.base import ContentFile
# from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from meals.models import (Ingredient, Tag, Recipe, RecipeIngredient,
                          Favorite, ShoppingCart)
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
    """."""

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
        """."""

        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'description', 'cook_time'
        )

    def get_is_favorited(self, obj):
        """."""
        user = self.context['request'].user
        return (
            user.is_authenticated
            and Favorite.objects.filter(user=user, recipe=obj).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        """."""
        user = self.context['request'].user
        return (
            user.is_authenticated
            and ShoppingCart.objects.filter(user=user, recipe=obj).exists()
        )

    def validate(self, data):
        """."""
        tags = self.initial_data.get('tags', [])
        ingredients = self.initial_data.get('ingredients', [])
        # валидация тегов
        if not tags:
            raise ValidationError(
                {'tags': 'Необходимо указать хотя бы один тег'}
            )
        try:
            tags = [int(tag) for tag in tags]
        except (ValueError, TypeError):
            raise ValidationError({'tags': 'Неверный формат тегов'})
        existing_tags = Tag.objects.filter(slug__in=tags)
        if len(existing_tags) != len(tags):
            found_tag = {tag.slug for tag in existing_tags}
            not_found_tag = [tag for tag in tags if tag not in found_tag]
            raise ValidationError({
                'tags': f'Теги со слагом {not_found_tag} не найдены'
            })
        unique_tags = set(tags)
        if len(unique_tags) != len(tags):
            duplicates_tags = [tag for tag in tags if tags.count(tag) > 1]
            raise ValidationError({
                'tags': f'Найдены дубликаты тегов:'
                f'{list(set(duplicates_tags))}'
            })
        # валидация ингридиентов
        if not ingredients:
            raise ValidationError(
                {'ingredients': 'Добавьте минимум один ингредиент'}
            )
        for ingredient in ingredients:
            if 'id' not in ingredient or 'amount' not in ingredient:
                raise ValidationError({
                    'ingredients': 'Неверный формат ингредиента'
                })
        ingredient_ids = [ingredient['id'] for ingredient in ingredients]
        existing_ingredients = Ingredient.objects.filter(id__in=ingredient_ids)
        found_ingredient = {
            ingredient.id for ingredient in existing_ingredients
        }
        not_found_ingredient = [
            ingredient for ingredient in ingredients
            if ingredient not in found_ingredient
        ]
        if not_found_ingredient:
            raise ValidationError({
                'ingredients': f'Ингредиенты с ID:'
                f'{not_found_ingredient} не найдены'
            })
        unique_ingredients = set(ingredient_ids)
        if len(unique_ingredients) != len(ingredient_ids):
            duplicates_ingredients = [
                ingredient for ingredient in ingredient_ids
                if ingredients.count(ingredient) > 1
            ]
            raise ValidationError({
                'ingredients': f'Найдены дубликаты ингредиентов:'
                f'{list(set(duplicates_ingredients))}'
            })
        for ingredient in ingredients:
            if ingredient['amount'] <= 0:
                raise ValidationError({
                    'ingredients': f'Количество для ингредиента'
                    f'{ingredient["id"]} должно быть больше 0'
                })
        ingredients_map = {
            ingredient.id: ingredient for ingredient in existing_ingredients
        }
        validated_ingredients = []
        for ingredient in ingredients:
            ingredient = ingredients_map[ingredient['id']]
            validated_ingredients.append({
                'ingredient': ingredient,
                'amount': ingredient['amount']
            })

        data['validated_tags'] = existing_tags
        data['validated_ingredients'] = validated_ingredients
        return data

    def create_ingredients(self, recipe, ingredients_data):
        """."""
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=recipe,
                ingredient=item['ingredient'],
                amount=item['amount']
            ) for item in ingredients_data
        ])

    def create(self, validated_data):
        """."""
        ingredients = validated_data.pop('validated_ingredients')
        tags = validated_data.pop('validated_tags')
        recipe = Recipe.objects.create(
            **validated_data,
            author=self.context['request'].user
        )
        recipe.tags.add(*tags)
        self.create_ingredients(recipe, ingredients)
        return recipe

    def update(self, instance, validated_data):
        """."""
        ingredients = validated_data.pop('validated_ingredients', None)
        tags = self.initial_data.get('validated_tags', None)
        instance = super().update(instance, validated_data)
        if tags is not None:
            instance.tags.clear()
            instance.tags.add(*tags)
        if ingredients is not None:
            instance.ingredients.clear()
            self.create_ingredients(instance, ingredients)
        return instance

    def to_representation(self, instance):
        """."""
        representation = super().to_representation(instance)
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            representation['is_favorited'] = (
                instance.favorites.filter(user=request.user).exists()
            )
            representation['is_in_shopping_cart'] = (
                instance.shopping_carts.filter(user=request.user).exists()
            )
        return representation


class SubscriptionSerializer(serializers.ModelSerializer):
    """."""

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
    profile_image = Base64ImageField(
        source='author.profile_image', read_only=True
    )

    class Meta:
        """."""

        model = Subscription
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'recipes', 'recipes_count', 'profile_image'
        )

    def get_is_subscribed(self, obj):
        """."""
        return True

    def get_recipes(self, obj):
        """."""
        request = self.context.get('request')
        limit = request.query_params.get('recipes_limit')
        recipes = obj.author.recipes.all()
        if limit:
            recipes = recipes[:int(limit)]
        return RecipeMinifiedSerializer(recipes, many=True).data

    def get_recipes_count(self, obj):
        """."""
        return obj.author.recipes.count()

    def get_profile_image(self, obj):
        """."""
        author = obj.author
        return author.profile_image.url if author.profile_image else None


class SetPasswordSerializer(serializers.Serializer):
    """."""

    new_password = serializers.CharField(required=True)
    current_password = serializers.CharField(required=True)
