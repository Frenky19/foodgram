import base64
import uuid

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from rest_framework import serializers

from recipes.models import (Ingredient, Recipe, RecipeIngredient, Tag)
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
    is_favorited = serializers.BooleanField(read_only=True)
    is_in_shopping_cart = serializers.BooleanField(read_only=True)
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
            if not isinstance(amount, str) or not amount.isdigit():
                raise serializers.ValidationError(
                    'Количество должно быть числом'
                )
            ingredient = get_object_or_404(Ingredient, id=ingredient_id)
            if ingredient_id in ingredient_ids:
                raise serializers.ValidationError(
                    f'Ингредиент {ingredient.name} указан дважды'
                )
            ingredient_ids.add(ingredient_id)
            if int(amount) < MIN_AMOUNT:
                raise serializers.ValidationError(
                    f'Количество {ingredient.name} '
                    f'должно быть не менее {MIN_AMOUNT}'
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
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        instance = super().update(instance, validated_data)
        instance.ingredient_list.all().delete()
        self.create_ingredients(instance, ingredients)
        instance.tags.set(tags)
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
    recipes_count = serializers.IntegerField(default=0)

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
        if limit and limit.isdigit():  # Проверка, что limit — строка из цифр
            recipes = recipes[:int(limit)]
        return RecipeMinifiedSerializer(
            recipes,
            many=True,
            context=self.context
        ).data


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


class RecipeGetShortLinkSerializer(serializers.Serializer):
    """Сокращённая ссылка для доступа к рецепту."""

    short_link = serializers.URLField()
