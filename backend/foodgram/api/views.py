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
from api.filters import RecipeFilter
from api.utils import generate_shopping_list, generate_pdf_response, generate_csv_response, generate_txt_response


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
    """
    Получение списка рецептов с возможностью фильтрации.

    Параметры запроса:
    - name - поиск по названию (частичное совпадение, без учета регистра)
    - author - фильтр по ID автора
    - tags - фильтр по слагам тегов (можно несколько через &)
    - is_favorited - показать только избранное
    - is_in_shopping_cart - показать только в корзине

    Примеры:
    - /api/recipes/?name=пицца
    - /api/recipes/?tags=breakfast&tags=dinner
    - /api/recipes/?author=2&is_favorited=1
    """

    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_queryset(self):
        """."""
        queryset = super().get_queryset()
        return queryset.select_related('author').prefetch_related(
            'tags',
            'ingredients',
            'recipe_ingredients__ingredient'
        ).distinct()

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


class ShoppingCartViewSet(viewsets.ViewSet):
    """."""

    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def download_shopping_cart(self, request):
        """."""
        format = request.query_params.get('format', 'txt')
        content = generate_shopping_list(request.user)

        if format == 'pdf':
            return generate_pdf_response(content, request.user)
        elif format == 'csv':
            return generate_csv_response(content)
        else:  # txt по умолчанию
            return generate_txt_response(content)
