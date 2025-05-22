from django_filters import rest_framework as django_filters
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from api.filters import RecipeFilter
from api.permissions import IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly
from api.serializers import (CustomUserSerializer, IngredientSerializer,
                             RecipeMinifiedSerializer, RecipeSerializer,
                             SubscriptionSerializer, TagSerializer)
from api.utils import (generate_csv_response, generate_pdf_response,
                       generate_shopping_list, generate_shopping_list_text,
                       generate_txt_response)
from meals.models import Favorite, Ingredient, Recipe, ShoppingCart, Tag
from users.models import Subscription, User


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet для работы с пользователями.

    Поддерживает стандартные CRUD-операции, а также:
    - Получение данных текущего пользователя
    - Подписку/отписку на других пользователей
    """

    queryset = User.objects.all()
    serializer_class = CustomUserSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['get'],
            permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        """Получение профиля текущего аутентифицированного пользователя."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[permissions.IsAuthenticated])
    def subscribe(self, request, pk=None):
        """
        Управление подписками на пользователей.

        POST: Создание подписки на пользователя
        DELETE: Удаление подписки на пользователя
        """
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
    """
    ViewSet для работы с тегами (только чтение).

    Возвращает список всех тегов, поддерживает поиск по slug.
    Пагинация отключена.
    """

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet для работы с ингредиентами (только чтение).

    Возвращает список всех ингредиентов, поддерживает поиск по имени.
    Пагинация отключена.
    """

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    pagination_class = None


class RecipeViewSet(viewsets.ModelViewSet):
    """
    ViewSet для работы с рецептами.

    Поддерживает:
    - CRUD-операции для рецептов
    - Фильтрацию по различным параметрам
    - Добавление/удаление в избранное и список покупок
    - Кастомные действия с рецептами

    Фильтрация доступна по параметрам:
    - name: поиск по названию (регистронезависимый, частичное совпадение)
    - author: ID автора рецепта
    - tags: slug тегов (можно несколько через &)
    - is_favorited: 1/0 для фильтрации избранных рецептов
    - is_in_shopping_cart: 1/0 для фильтрации рецептов в списке покупок
    """

    queryset = Recipe.objects.all()
    serializer_class = RecipeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    filter_backends = [django_filters.DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_queryset(self):
        """Оптимизация запросов к БД."""
        queryset = super().get_queryset()
        return queryset.select_related('author').prefetch_related(
            'tags',
            'ingredients',
            'recipe_ingredients__ingredient'
        ).distinct()

    def perform_create(self, serializer):
        """Автоматическое назначение текущего пользователя автором рецепта."""
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[permissions.IsAuthenticated])
    def favorite(self, request, pk=None):
        """Добавление/удаление рецепта в избранное."""
        return self._change_relation(Favorite, request, pk)

    @action(detail=True, methods=['post', 'delete'],
            permission_classes=[permissions.IsAuthenticated])
    def shopping_cart(self, request, pk=None):
        """Добавление/удаление рецепта в список покупок."""
        return self._change_relation(ShoppingCart, request, pk)

    def _change_relation(self, model, request, pk):
        """
        Общий метод для управления связями рецептов с пользователем.

        Аргументы:
        - model: класс модели связи (Favorite или ShoppingCart)
        - request: объект запроса
        - pk: ID рецепта
        """
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
    """
    ViewSet для работы со списком покупок.

    Поддерживает генерацию списка покупок в различных форматах.
    """

    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def download_shopping_cart(self, request):
        """
        Скачивание списка покупок в выбранном формате.

        Доступные форматы (параметр 'format'):
        - txt: текстовый файл (по умолчанию)
        - csv: CSV-файл
        - pdf: PDF-документ
        """
        format = request.query_params.get('format', 'txt')
        content = generate_shopping_list(request.user)
        text = generate_shopping_list_text(content)

        if format == 'txt':
            return generate_txt_response(text)
        elif format == 'csv':
            return generate_csv_response(content)
        else:
            return generate_pdf_response(content, request.user)
