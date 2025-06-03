import base64
import uuid

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework import serializers

from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from users.models import Subscription
from utils.constants import MIN_AMOUNT

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    """Декодирование изображений в формате base64."""

    def to_internal_value(self, data):
        """Преобразует строку base64 в объект изображения.

        Args:
            data: Входные данные (строка base64 или обычный файл)

        Returns:
            ContentFile: Объект файла изображения
        """
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(
                base64.b64decode(imgstr),
                name=f'{uuid.uuid4()}.{ext}'
            )
        return super().to_internal_value(data)


class UserSerializer(serializers.ModelSerializer):
    """Представление данных пользователя с подпиской и аватаром."""

    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        """Поля и модель для сериализации пользователя."""

        model = User
        fields = (
            'email', 'id', 'username',
            'first_name', 'last_name',
            'is_subscribed', 'avatar'
        )

    def get_is_subscribed(self, obj):
        """Проверка подписки текущего пользователя на данного автора.

        Args:
            obj: Объект пользователя для проверки

        Returns:
            bool: True если подписка существует, иначе False
        """
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(
                user=request.user,
                author=obj
            ).exists()
        return False

    def get_avatar(self, obj):
        """Получение абсолютного URL аватара пользователя.

        Args:
            obj: Объект пользователя

        Returns:
            str: Полный URL аватара или None
        """
        if obj.avatar:
            return self.context['request'].build_absolute_uri(obj.avatar.url)
        return None


class UserCreateSerializer(serializers.ModelSerializer):
    """Регистрация новых пользователей в системе."""

    class Meta:
        """Поля и модель для создания пользователя."""

        model = User
        fields = (
            'email', 'id', 'username',
            'first_name', 'last_name', 'password'
        )
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        """Создание нового пользователя с валидированными данными.

        Args:
            validated_data: Проверенные данные пользователя

        Returns:
            User: Созданный объект пользователя
        """
        user = User.objects.create_user(**validated_data)
        return user


class SetPasswordSerializer(serializers.Serializer):
    """Обновление пароля текущего пользователя."""

    new_password = serializers.CharField(required=True)
    current_password = serializers.CharField(required=True)


class SetAvatarSerializer(serializers.ModelSerializer):
    """Обновление аватара профиля пользователя."""

    avatar = Base64ImageField()

    class Meta:
        """Поля и модель для обновления аватара."""

        model = User
        fields = ('avatar',)


class IngredientSerializer(serializers.ModelSerializer):
    """Представление данных об ингредиентах."""

    class Meta:
        """Поля и модель для сериализации ингредиентов."""

        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class TagSerializer(serializers.ModelSerializer):
    """Представление данных о тегах."""

    class Meta:
        """Поля и модель для сериализации тегов."""

        model = Tag
        fields = ('id', 'name', 'slug')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Ингредиенты в составе рецепта с количеством."""

    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        """Поля и модель для связи рецепта с ингредиентами."""

        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    """Краткое представление рецепта для списков."""

    image = serializers.SerializerMethodField()

    class Meta:
        """Поля и модель для сокращённого представления рецептов."""

        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')

    def get_image(self, obj):
        """Получение абсолютного URL изображения рецепта.

        Args:
            obj: Объект рецепта

        Returns:
            str: Полный URL изображения или None
        """
        if obj.image:
            return self.context['request'].build_absolute_uri(obj.image.url)
        return None


class RecipeSerializer(serializers.ModelSerializer):
    """Детальное представление рецепта с дополнительной информацией."""

    tags = TagSerializer(many=True, read_only=True)
    author = UserSerializer(read_only=True)
    ingredients = RecipeIngredientSerializer(
        many=True,
        source='ingredient_list',
        read_only=True
    )
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()

    class Meta:
        """Поля и модель для полного представления рецептов."""

        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time'
        )

    def get_image(self, obj):
        """Получение абсолютного URL изображения рецепта.

        Args:
            obj: Объект рецепта

        Returns:
            str: Полный URL изображения или None
        """
        if obj.image:
            return self.context['request'].build_absolute_uri(obj.image.url)
        return None

    def get_is_favorited(self, obj):
        """Проверяет, добавлен ли рецепт в избранное текущим пользователем.

        Args:
            obj: Объект рецепта

        Returns:
            bool: True если рецепт в избранном, иначе False
        """
        user = self.context['request'].user
        if user.is_authenticated:
            return Favorite.objects.filter(
                user=user,
                recipe=obj
            ).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        """Проверяет, добавлен ли рецепт в корзину текущим пользователем.

        Args:
            obj: Объект рецепта

        Returns:
            bool: True если рецепт в корзине, иначе False
        """
        user = self.context['request'].user
        if user.is_authenticated:
            return ShoppingCart.objects.filter(
                user=user,
                recipe=obj
            ).exists()
        return False


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
    """Создание и обновление рецептов с валидацией данных."""

    ingredients = serializers.ListField(
        child=serializers.DictField(),
        write_only=True
    )
    tags = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Tag.objects.all(),
        write_only=True
    )
    image = Base64ImageField()

    class Meta:
        """Поля и модель для создания/обновления рецептов."""

        model = Recipe
        fields = (
            'ingredients', 'tags', 'image',
            'name', 'text', 'cooking_time'
        )
        extra_kwargs = {
            'name': {'required': True},
            'text': {'required': True},
            'cooking_time': {'required': True},
        }

    def validate_ingredients(self, value):
        """Проверка корректности списка ингредиентов.

        Args:
            value: Список ингредиентов для валидации

        Returns:
            list: Валидированный список ингредиентов

        Raises:
            ValidationError: Если ингредиенты не соответствуют требованиям
        """
        if not value:
            raise serializers.ValidationError(
                'Добавьте хотя бы один ингредиент'
            )
        validated_ingredients = []
        ingredient_ids = set()
        for item in value:
            ingredient_id = item.get('id')
            amount = item.get('amount')
            if not ingredient_id or not amount:
                raise serializers.ValidationError(
                    'Неверный формат ингредиента'
                )
            try:
                ingredient = Ingredient.objects.get(id=ingredient_id)
            except Ingredient.DoesNotExist:
                raise serializers.ValidationError(
                    f'Ингредиент с ID {ingredient_id} не существует'
                )
            if ingredient_id in ingredient_ids:
                raise serializers.ValidationError(
                    f'Ингредиент {ingredient.name} указан дважды'
                )
            ingredient_ids.add(ingredient_id)
            if int(amount) < MIN_AMOUNT:
                raise serializers.ValidationError(
                    f'Количество {ingredient.name}'
                    f' должно быть не менее {MIN_AMOUNT}'
                )
            validated_ingredients.append({
                'ingredient': ingredient,
                'amount': amount
            })
        return validated_ingredients

    def validate_tags(self, value):
        """Проверка корректности списка тегов.

        Args:
            value: Список тегов для валидации

        Returns:
            list: Валидированный список тегов

        Raises:
            ValidationError: Если теги не соответствуют требованиям
        """
        if not value:
            raise serializers.ValidationError('Добавьте хотя бы один тег')
        tag_ids = [tag.id for tag in value]
        if len(tag_ids) != len(set(tag_ids)):
            raise serializers.ValidationError('Теги должны быть уникальными')
        return value

    def create_ingredients(self, recipe, ingredients):
        """Создание связей между рецептом и ингредиентами.

        Args:
            recipe: Объект рецепта
            ingredients: Список ингредиентов для связи
        """
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=recipe,
                ingredient=item['ingredient'],
                amount=item['amount']
            ) for item in ingredients
        ])

    def create(self, validated_data):
        """Создание нового рецепта со связанными данными.

        Args:
            validated_data: Проверенные данные рецепта

        Returns:
            Recipe: Созданный объект рецепта
        """
        user = self.context['request'].user
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        recipe = Recipe.objects.create(
            author=user,
            **validated_data
        )
        self.create_ingredients(recipe, ingredients)
        recipe.tags.set(tags)
        return recipe

    def update(self, instance, validated_data):
        """Обновление существующего рецепта и его связей.

        Args:
            instance: Существующий объект рецепта
            validated_data: Проверенные данные для обновления

        Returns:
            Recipe: Обновленный объект рецепта
        """
        for key, value in validated_data.items():
            if key not in ['ingredients', 'tags']:
                setattr(instance, key, value)
        instance.save()
        if 'ingredients' in validated_data:
            instance.ingredient_list.all().delete()
            self.create_ingredients(
                instance, validated_data.pop('ingredients')
            )
        if 'tags' in validated_data:
            instance.tags.set(validated_data.pop('tags'))
        return instance

    def to_representation(self, instance):
        """Преобразование объекта рецепта в сериализованный формат.

        Args:
            instance: Объект рецепта

        Returns:
            dict: Сериализованные данные рецепта
        """
        return RecipeSerializer(
            instance,
            context=self.context
        ).data


class UserWithRecipesSerializer(UserSerializer):
    """Представление пользователя с его рецептами."""

    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        """Поля и модель для пользователя с рецептами."""

        fields = UserSerializer.Meta.fields + (
            'recipes', 'recipes_count'
        )

    def get_recipes(self, obj):
        """Получение рецептов пользователя с ограничением количества.

        Args:
            obj: Объект пользователя

        Returns:
            list: Сериализованные данные рецептов
        """
        request = self.context.get('request')
        limit = request.query_params.get('recipes_limit') if request else None
        recipes = obj.recipes.all()
        if limit:
            try:
                recipes = recipes[:int(limit)]
            except ValueError:
                pass
        return RecipeMinifiedSerializer(
            recipes,
            many=True,
            context=self.context
        ).data

    def get_recipes_count(self, obj):
        """Получение общего количества рецептов пользователя.

        Args:
            obj: Объект пользователя

        Returns:
            int: Количество рецептов
        """
        return obj.recipes.count()


class SubscriptionSerializer(serializers.ModelSerializer):
    """Создание подписок на других пользователей."""

    class Meta:
        """Поля и модель для подписок."""

        model = Subscription
        fields = ('user', 'author')

    def validate(self, data):
        """Проверка валидности данных для подписки.

        Args:
            data: Данные для создания подписки

        Returns:
            dict: Проверенные данные

        Raises:
            ValidationError: Если подписка невалидна
        """
        if data['user'] == data['author']:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя'
            )
        if Subscription.objects.filter(
            user=data['user'],
            author=data['author']
        ).exists():
            raise serializers.ValidationError(
                'Вы уже подписаны на этого пользователя'
            )
        return data


class TokenCreateSerializer(serializers.Serializer):
    """Аутентификация пользователя по email и паролю."""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True)


class RecipeGetShortLinkSerializer(serializers.Serializer):
    """Сокращённая ссылка для доступа к рецепту."""

    short_link = serializers.URLField()
