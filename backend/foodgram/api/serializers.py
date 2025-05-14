import base64
import datetime as dt
from django.core.files.base import ContentFile
from rest_framework import serializers
from meals.models import Ingredient, Tag, Recipe
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


class IngridientSerializer(serializers.ModelSerializer):
    """."""

    class Meta:
        """."""

        model = Ingredient
        fields = ('title', 'unit')


class TagSerializer(serializers.ModelSerializer):
    """."""

    class Meta:
        """."""

        model = Tag
        fields = ('title', 'slug')


class RecipeSerializer(serializers.ModelSerializer):
    """."""

    ingredients = IngridientSerializer(many=True)

    class Meta:
        """."""

        model = Recipe
        fields = ('title',)


class UserSerializer(serializers.ModelSerializer):
    """."""

    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        """."""

        model = User
        fields = ('id', 'email', 'username', 'first_name',
                  'last_name', 'is_subscribed', 'profile_image')

    def get_is_subscribed(self, obj):
        """."""
        request = self.context.get('request')
        return Subscription.objects.filter(
            user=request.user,
            author=obj
        ).exists() if request else False
