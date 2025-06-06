from django_filters.rest_framework import DjangoFilterBackend


class RecipeFilter(DjangoFilterBackend):
    """Фильтрация рецептов по автору, тегам и пользовательским спискам."""

    def filter_queryset(self, request, queryset, view):
        """Фильтрация рецептов по параметрам запроса."""
        author_id = request.query_params.get('author')
        if author_id:
            queryset = queryset.filter(author_id=author_id)
        tags = request.query_params.getlist('tags')
        if tags:
            queryset = queryset.filter(tags__slug__in=tags).distinct()
        is_favorited = request.query_params.get('is_favorited')
        if is_favorited and request.user.is_authenticated:
            if is_favorited == '1':
                queryset = queryset.filter(favorites__user=request.user)
        is_in_shopping_cart = request.query_params.get('is_in_shopping_cart')
        if is_in_shopping_cart and request.user.is_authenticated:
            if is_in_shopping_cart == '1':
                queryset = queryset.filter(shopping_carts__user=request.user)
        return queryset
