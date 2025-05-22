import base64

from django.core.files.base import ContentFile
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework.validators import UniqueTogetherValidator

from meals.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                          ShoppingCart, Tag)
from users.models import Subscription, User


class Base64ImageField(serializers.ImageField):
    """
    Кастомное поле для работы с изображениями в формате base64.

    Преобразует строку base64 в файл изображения при десериализации.
    Наследуется от стандартного ImageField с добавлением обработки base64.
    """

    def to_internal_value(self, data):
        """Преобразует строку base64 в объект файла изображения."""
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)
        return super().to_internal_value(data)


class IngredientInRecipeSerializer(serializers.ModelSerializer):
    """
    Сериализатор для отображения ингредиентов в составе рецепта.

    Включает дополнительные поля для отображения информации об ингредиенте.
    """

    id = serializers.PrimaryKeyRelatedField(
        queryset=Ingredient.objects.all(),
        source='ingredient.id'
    )
    name = serializers.CharField(
        source='ingredient.name',
        read_only=True
    )
    measurement_unit = serializers.CharField(
        source='ingredient.measurement_unit',
        read_only=True
    )

    class Meta:
        """Мета-класс для IngredientInRecipeSerializer."""

        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class IngredientSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Ingredient.

    Используется для операций CRUD с ингредиентами.
    """

    class Meta:
        """Мета-класс для IngredientSerializer."""

        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class TagSerializer(serializers.ModelSerializer):
    """
    Сериализатор для модели Tag.

    Используется для работы с тегами рецептов.
    """

    class Meta:
        """Мета-класс для TagSerializer."""

        model = Tag
        fields = ('id', 'name', 'slug')


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    """
    Упрощенный сериализатор для краткого отображения рецептов.

    Используется в списках и подписках.
    """

    image = Base64ImageField(required=False, allow_null=True)

    class Meta:
        """Мета-класс для RecipeMinifiedSerializer."""

        model = Recipe
        fields = ('id', 'name', 'image', 'cook_time')

    def get_image(self, obj):
        """Получает URL изображения рецепта."""
        return obj.image.url if obj.image else None


class CustomUserSerializer(serializers.ModelSerializer):
    """Сериализатор для модели пользователя с расширенными полями."""

    # is_subscribed = serializers.SerializerMethodField()
    # avatar = Base64ImageField(required=False, allow_null=True)

    class Meta:
        """Мета-класс для CustomUserSerializer."""

        model = User
        fields = (
            'id', 'email', 'username', 'first_name',
            'last_name'  # , 'is_subscribed', 'avatar'
        )

    def get_is_subscribed(self, obj):
        """Проверяет подписку текущего пользователя на автора."""
        user = self.context['request'].user
        return (
            user.is_authenticated and Subscription.objects.filter(
                user=user, author=obj
            ).exists()
        )

    def get_avatar(self, obj):
        """Получает URL аватара пользователя."""
        return obj.avatar.url if obj.avatar else None


class UserWithRecipesSerializer(CustomUserSerializer):
    """
    Расширенный сериализатор пользователя с информацией о рецептах.

    Добавляет поля:
    - recipes: список рецептов пользователя
    - recipes_count: общее количество рецептов
    """

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(CustomUserSerializer.Meta):
        """Мета-класс с дополнительными полями."""

        fields = (
            CustomUserSerializer.Meta.fields + ('recipes', 'recipes_count')
        )

    def get_recipes(self, obj):
        """Получает список рецептов пользователя с возможностью лимита."""
        request = self.context['request']
        recipes_limit = request.query_params.get('recipes_limit')
        queryset = obj.recipes.all()
        if recipes_limit:
            queryset = queryset[:int(recipes_limit)]
        return RecipeMinifiedSerializer(queryset, many=True).data

    def get_recipes_count(self, obj):
        """Считает общее количество рецептов пользователя."""
        return obj.recipes.count()


class RecipeSerializer(serializers.ModelSerializer):
    """
    Основной сериализатор для работы с рецептами.

    Включает:
    - Полную информацию о рецепте
    - Флаги избранного и корзины покупок
    - Валидацию тегов и ингредиентов
    - Поддержку base64 для изображений
    """

    tags = TagSerializer(many=True, read_only=True)
    author = CustomUserSerializer(read_only=True)
    ingredients = IngredientInRecipeSerializer(
        many=True,
        source='recipe_ingredients'
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField()

    class Meta:
        """Мета-класс для RecipeSerializer."""

        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'description', 'cook_time'
        )
        validators = [
            UniqueTogetherValidator(
                queryset=Recipe.objects.all(),
                fields=['author', 'name']
            )
        ]

    def get_is_favorited(self, obj):
        """Проверяет наличие рецепта в избранном у текущего пользователя."""
        user = self.context['request'].user
        return (
            user.is_authenticated
            and Favorite.objects.filter(user=user, recipe=obj).exists()
        )

    def get_is_in_shopping_cart(self, obj):
        """Проверяет наличие рецепта в корзине покупок."""
        user = self.context['request'].user
        return (
            user.is_authenticated
            and ShoppingCart.objects.filter(user=user, recipe=obj).exists()
        )

    def validate(self, data):
        """
        Основная валидация данных рецепта.

        Проверяет:
        - Наличие и корректность тегов
        - Наличие и корректность ингредиентов
        - Уникальность ингредиентов
        - Положительность количества ингредиентов
        """
        tags = self.initial_data.get('tags', [])
        ingredients = self.initial_data.get('ingredients', [])

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
        if not ingredients:
            raise ValidationError(
                {'ingredients': 'Добавьте минимум один ингредиент'}
            )
        for item in ingredients:
            if 'ingredient' not in item or 'amount' not in item:
                raise ValidationError(
                    {'ingredients': 'Неверный формат ингредиента'}
                )
            if 'id' not in item['ingredient']:
                raise ValidationError(
                    {'ingredients': 'Отсутствует ID ингредиента'}
                )
        ingredient_ids = [item['ingredient']['id'] for item in ingredients]
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
        """Создает связи между рецептом и ингредиентами."""
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=recipe,
                ingredient=item['ingredient'],
                amount=item['amount']
            ) for item in ingredients_data
        ])

    def create(self, validated_data):
        """Создает новый рецепт с привязкой тегов и ингредиентов."""
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
        """Обновляет существующий рецепт."""
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
        """Добавляет флаги избранного и корзины к представлению."""
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
    """
    Сериализатор для подписок на пользователей.

    Включает полную информацию об авторе и его рецептах.
    """

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
    avatar = Base64ImageField(
        source='author.avatar', read_only=True
    )

    class Meta:
        """Мета-класс для SubscriptionSerializer."""

        model = Subscription
        fields = (
            'email', 'id', 'username', 'first_name', 'last_name',
            'is_subscribed', 'recipes', 'recipes_count', 'avatar'
        )

    def get_is_subscribed(self, obj):
        """Всегда возвращает True, так как объект представляет подписку."""
        return True

    def get_recipes(self, obj):
        """Получает рецепты автора с возможностью ограничения количества."""
        request = self.context.get('request')
        limit = request.query_params.get('recipes_limit')
        recipes = obj.author.recipes.all()
        if limit:
            recipes = recipes[:int(limit)]
        return RecipeMinifiedSerializer(recipes, many=True).data

    def get_recipes_count(self, obj):
        """Считает общее количество рецептов автора."""
        return obj.author.recipes.count()

    def get_avatar(self, obj):
        """Устанавливает аватар пользователя."""
        author = obj.author
        return author.avatar.url if author.avatar else None


class SetPasswordSerializer(serializers.Serializer):
    """Сериализатор для смены пароля пользователя."""

    new_password = serializers.CharField(required=True)
    current_password = serializers.CharField(required=True)
