from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from api.permissions import IsAuthorOrReadOnly, IsAuthenticatedOrReadOnly
from api.serializers import (TagSerializer, IngredientSerializer,
                             RecipeSerializer, UserSerializer,
                             RecipeMinifiedSerializer, SubscriptionSerializer)
from meals.models import Tag, Ingredient, Recipe, Tag, Favorite, ShoppingCart
from users.models import Subscription, User
from django_filters import rest_framework as django_filters
from .filters import RecipeFilter


class UserViewSet(viewsets.ModelViewSet):
    """."""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['get'],
            permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[permissions.IsAuthenticated])
    def subscribe(self, request, pk=None):
        """."""
        author = self.get_object()
        subscription = Subscription.objects.filter(
            user=request.user,
            author=author
        )

        if request.method == 'POST':
            if subscription.exists():
                return Response(
                    {'errors': 'Вы уже подписаны на этого пользователя'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if request.user == author:
                return Response(
                    {'errors': 'Нельзя подписаться на самого себя'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            Subscription.objects.create(user=request.user, author=author)
            serializer = SubscriptionSerializer(
                subscription.get(),
                context={'request': request}
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            if not subscription.exists():
                return Response(
                    {'errors': 'Подписка не найдена'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)


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
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_queryset(self):
        """."""
        queryset = super().get_queryset()
        queryset = queryset.select_related('author')
        queryset = queryset.prefetch_related(
            'tags',
            'ingredients',
            'recipe_ingredients'
        )
        return queryset

    def perform_create(self, serializer):
        """."""
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[permissions.IsAuthenticated])
    def favorite(self, request, pk=None):
        """."""
        return self._change_relation(Favorite, request, pk)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[permissions.IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        """."""
        return self._change_relation(ShoppingCart, request, pk)

    def _change_relation(self, model, request, pk):
        recipe = self.get_object()
        user = request.user
        relation = model.objects.filter(user=user, recipe=recipe)

        if request.method == 'POST':
            if relation.exists():
                return Response(
                    {'errors': 'Рецепт уже добавлен'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            model.objects.create(user=user, recipe=recipe)
            serializer = RecipeMinifiedSerializer(recipe)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        if request.method == 'DELETE':
            if not relation.exists():
                return Response(
                    {'errors': 'Рецепт не найден'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            relation.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
