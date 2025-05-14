from rest_framework import viewsets, permissions
from users.models import User
from meals.models import Tag, Ingredient, Recipe
from api.serializers import TagSerializer, IngredientSerializer, RecipeSerializer, UserSerializer


class UserViewSet(viewsets.ModelViewSet):
    """."""

    queryset = User.objects.all()
    serializer_class = UserSerializer


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    """."""

    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
