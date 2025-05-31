import base64
import uuid

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from rest_framework import serializers

from recipes.models import (
    Favorite,
    Ingredient,
    Recipe,
    RecipeIngredient,
    RecipeTags,
    ShoppingCart,
    Tag
)
from users.models import Subscription
from utils.constants import MIN_AMOUNT

User = get_user_model()


class Base64ImageField(serializers.ImageField):
    """Кастомное поле для обработки изображений в base64."""
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(
                base64.b64decode(imgstr),
                name=f'{uuid.uuid4()}.{ext}'
            )
        return super().to_internal_value(data)


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для пользователя."""
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'email', 'id', 'username', 
            'first_name', 'last_name', 
            'is_subscribed', 'avatar'
        )

    def get_is_subscribed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Subscription.objects.filter(
                user=request.user, 
                author=obj
            ).exists()
        return False

    def get_avatar(self, obj):
        if obj.avatar:
            return self.context['request'].build_absolute_uri(obj.avatar.url)
        return None


class UserCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для регистрации пользователя."""
    class Meta:
        model = User
        fields = (
            'email', 'id', 'username',
            'first_name', 'last_name', 'password'
        )
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class SetPasswordSerializer(serializers.Serializer):
    """Сериализатор для изменения пароля."""
    new_password = serializers.CharField(required=True)
    current_password = serializers.CharField(required=True)


class SetAvatarSerializer(serializers.ModelSerializer):
    """Сериализатор для обновления аватара."""
    avatar = Base64ImageField()

    class Meta:
        model = User
        fields = ('avatar',)


class IngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов."""
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов."""
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class RecipeIngredientSerializer(serializers.ModelSerializer):
    """Сериализатор для ингредиентов в рецепте."""
    id = serializers.ReadOnlyField(source='ingredient.id')
    name = serializers.ReadOnlyField(source='ingredient.name')
    measurement_unit = serializers.ReadOnlyField(
        source='ingredient.measurement_unit'
    )

    class Meta:
        model = RecipeIngredient
        fields = ('id', 'name', 'measurement_unit', 'amount')


class RecipeMinifiedSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор для рецептов (корзина/избранное)."""
    image = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')

    def get_image(self, obj):
        if obj.image:
            return self.context['request'].build_absolute_uri(obj.image.url)
        return None


class RecipeSerializer(serializers.ModelSerializer):
    """Основной сериализатор для рецептов."""
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
        model = Recipe
        fields = (
            'id', 'tags', 'author', 'ingredients',
            'is_favorited', 'is_in_shopping_cart',
            'name', 'image', 'text', 'cooking_time'
        )

    def get_image(self, obj):
        if obj.image:
            return self.context['request'].build_absolute_uri(obj.image.url)
        return None

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return Favorite.objects.filter(
                user=user, 
                recipe=obj
            ).exists()
        return False

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return ShoppingCart.objects.filter(
                user=user, 
                recipe=obj
            ).exists()
        return False


class RecipeCreateUpdateSerializer(serializers.ModelSerializer):
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
        if not value:
            raise serializers.ValidationError("Добавьте хотя бы один ингредиент")
        
        validated_ingredients = []
        ingredient_ids = set()
        
        for item in value:
            ingredient_id = item.get('id')
            amount = item.get('amount')
            
            if not ingredient_id or not amount:
                raise serializers.ValidationError("Неверный формат ингредиента")
            
            try:
                ingredient = Ingredient.objects.get(id=ingredient_id)
            except Ingredient.DoesNotExist:
                raise serializers.ValidationError(f"Ингредиент с ID {ingredient_id} не существует")
            
            if ingredient_id in ingredient_ids:
                raise serializers.ValidationError(f"Ингредиент {ingredient.name} указан дважды")
                
            ingredient_ids.add(ingredient_id)
            
            if int(amount) < MIN_AMOUNT:
                raise serializers.ValidationError(
                    f"Количество {ingredient.name} должно быть не менее {MIN_AMOUNT}"
                )
                
            validated_ingredients.append({
                'ingredient': ingredient,
                'amount': amount
            })
        
        return validated_ingredients

    def validate_tags(self, value):
        if not value:
            raise serializers.ValidationError("Добавьте хотя бы один тег")
        
        tag_ids = [tag.id for tag in value]
        if len(tag_ids) != len(set(tag_ids)):
            raise serializers.ValidationError("Теги должны быть уникальными")
            
        return value

    def create_ingredients(self, recipe, ingredients):
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                recipe=recipe,
                ingredient=item['ingredient'],
                amount=item['amount']
            ) for item in ingredients
        ])

    def create_tags(self, recipe, tags):
        RecipeTags.objects.bulk_create([
            RecipeTags(recipe=recipe, tag=tag) for tag in tags
        ])

    def create(self, validated_data):
        # Извлекаем текущего пользователя из контекста
        user = self.context['request'].user
        
        # Извлекаем данные для связей
        ingredients = validated_data.pop('ingredients')
        tags = validated_data.pop('tags')
        
        # Создаем рецепт с автором
        recipe = Recipe.objects.create(
            author=user,
            **validated_data
        )
        
        # Создаем связанные объекты
        self.create_ingredients(recipe, ingredients)
        self.create_tags(recipe, tags)
        
        return recipe

    def update(self, instance, validated_data):
        # Обновляем только основные поля (исключая связи)
        for key, value in validated_data.items():
            if key not in ['ingredients', 'tags']:
                setattr(instance, key, value)
        instance.save()
        
        # Обновляем ингредиенты
        if 'ingredients' in validated_data:
            instance.ingredient_list.all().delete()
            self.create_ingredients(instance, validated_data.pop('ingredients'))
        
        # Обновляем теги через промежуточную модель
        if 'tags' in validated_data:
            # Удаляем старые связи
            RecipeTags.objects.filter(recipe=instance).delete()
            # Создаем новые связи
            self.create_tags(instance, validated_data.pop('tags'))
        
        return instance

    def to_representation(self, instance):
        return RecipeSerializer(
            instance,
            context=self.context
        ).data


class UserWithRecipesSerializer(UserSerializer):
    """Сериализатор для пользователя с рецептами."""
    recipes = serializers.SerializerMethodField()
    recipes_count = serializers.SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = UserSerializer.Meta.fields + (
            'recipes', 'recipes_count'
        )

    def get_recipes(self, obj):
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
        return obj.recipes.count()


class SubscriptionSerializer(serializers.ModelSerializer):
    """Сериализатор для подписок."""
    class Meta:
        model = Subscription
        fields = ('user', 'author')

    def validate(self, data):
        if data['user'] == data['author']:
            raise serializers.ValidationError(
                "Нельзя подписаться на самого себя"
            )
        if Subscription.objects.filter(
            user=data['user'],
            author=data['author']
        ).exists():
            raise serializers.ValidationError(
                "Вы уже подписаны на этого пользователя"
            )
        return data


class TokenCreateSerializer(serializers.Serializer):
    """Сериализатор для получения токена."""
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True)


class RecipeGetShortLinkSerializer(serializers.Serializer):
    """Сериализатор для короткой ссылки на рецепт."""
    short_link = serializers.URLField()
