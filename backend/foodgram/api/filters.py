from django_filters import rest_framework as filters
from meals.models import Recipe, Tag
from users.models import User


class RecipeFilter(filters.FilterSet):
    """."""

    is_favorited = filters.BooleanFilter(method='filter_is_favorited')
    is_in_shopping_cart = filters.BooleanFilter(
        method='filter_is_in_shopping_cart'
    )
    author = filters.ModelChoiceFilter(queryset=User.objects.all())
    tags = filters.ModelMultipleChoiceFilter(
        field_name='tags__slug',
        to_field_name='slug',
        queryset=Tag.objects.all()
    )
    name = filters.CharFilter(
        method='filter_by_name',
        label='Поиск по названию рецепта'
    )

    class Meta:
        """."""

        model = Recipe
        fields = (
            'author', 'tags', 'is_favorited', 'is_in_shopping_cart', 'name'
        )

    def filter_by_name(self, queryset, name, value):
        """
        Поиск по частичному совпадению в названии рецепта.

        Пример: /api/recipes/?name=суп
        """
        return queryset.filter(name__icontains=value)

    def filter_is_favorited(self, queryset, name, value):
        """."""
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(favorites__user=user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        """."""
        user = self.request.user
        if value and user.is_authenticated:
            return queryset.filter(shopping_carts__user=user)
        return queryset
