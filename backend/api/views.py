from django.contrib.auth import get_user_model
from django.db.models import (BooleanField, Count, Exists, OuterRef, Prefetch,
                              Sum, Value)
from django_filters.rest_framework import DjangoFilterBackend
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import (AllowAny, IsAuthenticated,
                                        IsAuthenticatedOrReadOnly)
from rest_framework.response import Response

from api.filters import IngredientFilter, RecipeFilter
from api.pagination import CustomPagination
from api.serializers import (IngredientSerializer,
                             RecipeCreateUpdateSerializer,
                             RecipeGetShortLinkSerializer,
                             RecipeRelationSerializer, RecipeSerializer,
                             SetAvatarSerializer, SetPasswordSerializer,
                             SubscriptionSerializer, TagSerializer,
                             UserCreateSerializer, UserSerializer,
                             UserWithRecipesSerializer)
from recipes.models import (Favorite, Ingredient, Recipe, RecipeIngredient,
                            ShoppingCart, Tag)
from users.models import Subscription

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    """Управление аккаунтами пользователей."""

    queryset = User.objects.all()
    serializer_class = UserSerializer
    pagination_class = CustomPagination
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от выполняемого действия."""
        if self.action == 'create':
            return UserCreateSerializer
        return super().get_serializer_class()

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def me(self, request):
        """Получение текущего пользователя."""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

    @action(
        detail=False,
        methods=['post'],
        permission_classes=[IsAuthenticated]
    )
    def set_password(self, request):
        """Изменение пароля текущего пользователя."""
        serializer = SetPasswordSerializer(
            data=request.data, context={'user': request.user}
        )
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['put'],
        permission_classes=[IsAuthenticated],
        parser_classes=[MultiPartParser, FormParser]
    )
    def avatar(self, request):
        """Обновление аватара текущего пользователя."""
        serializer = SetAvatarSerializer(request.user, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @avatar.mapping.delete
    def delete_avatar(self, request):
        """Удаление аватара текущего пользователя."""
        request.user.avatar.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthenticated]
    )
    def subscribe(self, request, pk=None):
        """Подписка/отписка на пользователя."""
        author = get_object_or_404(User, pk=pk)
        if request.method == 'POST':
            data = {'user': request.user.id, 'author': author.id}
            serializer = SubscriptionSerializer(
                data=data, context={'request': request}
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            subscription, _ = Subscription.objects.filter(
                user=request.user,
                author=author
            ).delete()
            if subscription == 0:
                return Response(
                    {'detail': 'Вы не были подписаны на этого автора.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated],
        url_path='subscriptions',
        url_name='subscriptions'
    )
    def subscriptions(self, request):
        """Получение списка подписок с рецептами."""
        user = request.user
        subscriptions = User.objects.filter(followers__user=user).annotate(
            recipes_count=Count('recipes')
        )
        page = self.paginate_queryset(subscriptions)
        recipes_limit = request.query_params.get('recipes_limit')
        context = self.get_serializer_context()
        if recipes_limit:
            context['recipes_limit'] = recipes_limit
        if page is not None:
            serializer = UserWithRecipesSerializer(
                page,
                many=True,
                context=context
            )
            return self.get_paginated_response(serializer.data)
        serializer = UserWithRecipesSerializer(
            subscriptions,
            many=True,
            context=context
        )
        return Response(serializer.data)


class TagViewSet(viewsets.ReadOnlyModelViewSet):
    """Просмотр доступных тегов для категорий рецептов."""

    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AllowAny]
    pagination_class = None


class IngredientViewSet(viewsets.ReadOnlyModelViewSet):
    """Поиск и просмотр ингредиентов для рецептов."""

    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    filter_backends = [DjangoFilterBackend]
    filterset_class = IngredientFilter


class RecipeViewSet(viewsets.ModelViewSet):
    """Управление рецептами: создание, просмотр, обновление, удаление."""

    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = CustomPagination
    filter_backends = [RecipeFilter]

    def get_queryset(self):
        """Аннотация queryset'а для добавления избранного и корзины."""
        base_queryset = Recipe.objects.select_related(
            'author'
        ).prefetch_related(
            'tags',
            Prefetch(
                'ingredient_list',
                queryset=RecipeIngredient.objects.select_related('ingredient')
            )
        )
        user = self.request.user
        if user.is_authenticated:
            return base_queryset.annotate(
                is_favorited=Exists(
                    Favorite.objects.filter(
                        user=user,
                        recipe=OuterRef('pk')
                    )
                ),
                is_in_shopping_cart=Exists(
                    ShoppingCart.objects.filter(
                        user=user,
                        recipe=OuterRef('pk')
                    )
                )
            )
        return base_queryset.annotate(
            is_favorited=Value(False, output_field=BooleanField()),
            is_in_shopping_cart=Value(False, output_field=BooleanField())
        )

    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия."""
        if self.action in ['create', 'update', 'partial_update']:
            return RecipeCreateUpdateSerializer
        return RecipeSerializer

    def perform_update(self, serializer):
        """Автоматически обновляет автора рецепта при изменении."""
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['post', 'delete'])
    def favorite(self, request, pk=None):
        """Добавление/удаление рецепта в избранное."""
        return self._handle_relation_action(
            request, pk, Favorite, 'избранном'
        )

    @action(detail=True, methods=['post', 'delete'])
    def shopping_cart(self, request, pk=None):
        """Добавление/удаление рецепта в корзину."""
        return self._handle_relation_action(
            request, pk, ShoppingCart, 'корзине'
        )

    def _handle_relation_action(self, request, pk, model, relation_name):
        """Обработка операций с пользовательскими списками (избранное/корзина).

        Args:
            request: Объект запроса
            pk: ID рецепта
            model: Модель отношения (Favorite или ShoppingCart)
            relation_name: Название отношения для сообщений
        """
        user = request.user
        if request.method == 'POST':
            recipe = get_object_or_404(Recipe, pk=pk)
            serializer = RecipeRelationSerializer(
                data={},
                context={
                    'request': request,
                    'recipe': recipe,
                    'model': model,
                    'relation_name': relation_name
                }
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            relation, _ = model.objects.filter(
                user=user, recipe_id=pk
            ).delete()
            if relation == 0:
                return Response(
                    {'detail': f'Рецепта нет в {relation_name}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthenticated]
    )
    def download_shopping_cart(self, request):
        """Генерация и скачивание списка покупок в формате TXT."""
        ingredients = RecipeIngredient.objects.filter(
            recipe__shopping_carts__user=request.user
        ).values(
            'ingredient__name',
            'ingredient__measurement_unit'
        ).annotate(
            total_amount=Sum('amount')
        ).order_by('ingredient__name')
        content = self._generate_shopping_list_content(ingredients)
        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = (
            'attachment; filename="shopping_list.txt"'
        )
        return response

    def _generate_shopping_list_content(self, ingredients):
        """Генерация текстового содержимого для списка покупок."""
        content = 'Список покупок:\n\n'
        for item in ingredients:
            content += (
                f'{item["ingredient__name"]} - '
                f'{item["total_amount"]} '
                f'{item["ingredient__measurement_unit"]}\n'
            )
        return content

    @action(detail=True, methods=['get'], url_path='get-link')
    def get_link(self, request, pk=None):
        """Генерация короткой ссылки на конкретный рецепт."""
        recipe = get_object_or_404(Recipe, pk=pk)
        short_link = request.build_absolute_uri(
            f'/api/recipes/{recipe.id}/'
        )
        serializer = RecipeGetShortLinkSerializer({
            'short_link': short_link
        })
        return Response(serializer.data)
