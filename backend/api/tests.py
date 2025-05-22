from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status

from meals.models import Tag, Ingredient, Recipe, Favorite, ShoppingCart
from users.models import Subscription, User


class UserViewSetTests(APITestCase):
    """Набор тестов для проверки функциональности UserViewSet."""

    def setUp(self):
        """Инициализация тестовых данных для пользователей."""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass'
        )
        self.other_user = User.objects.create_user(
            email='other@example.com',
            username='otheruser',
            password='otherpass'
        )
        self.client.force_authenticate(user=self.user)

    def test_retrieve_me(self):
        """
        Тестирование получения профиля текущего пользователя.

        Проверяет:
        - Статус ответа 200 OK
        - Корректность возвращаемых данных
        """
        url = reverse('user-me')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')

    def test_subscribe_create(self):
        """
        Тестирование создания подписки на другого пользователя.

        Проверяет:
        - Успешное создание подписки (201 Created)
        - Наличие записи в базе данных
        """
        url = reverse('user-subscribe', args=[self.other_user.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Subscription.objects.filter(
            user=self.user,
            author=self.other_user
        ).exists())

    def test_subscribe_delete(self):
        """
        Тестирование удаления подписки на пользователя.

        Проверяет:
        - Успешное удаление подписки (204 No Content)
        - Отсутствие записи в базе данных после удаления
        """
        Subscription.objects.create(user=self.user, author=self.other_user)
        url = reverse('user-subscribe', args=[self.other_user.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Subscription.objects.filter(
            user=self.user,
            author=self.other_user
        ).exists())


class TagViewSetTests(APITestCase):
    """Набор тестов для проверки работы с тегами (TagViewSet)."""

    def setUp(self):
        """Инициализация тестового тега."""
        self.tag = Tag.objects.create(
            name='Test Tag',
            slug='test-tag'
        )

    def test_list_tags(self):
        """
        Тестирование получения списка тегов.

        Проверяет:
        - Статус ответа 200 OK
        - Количество возвращаемых тегов
        """
        url = reverse('tag-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)


class RecipeViewSetTests(APITestCase):
    """Набор тестов для проверки функциональности RecipeViewSet."""

    def setUp(self):
        """Инициализация тестовых данных для рецептов."""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass'
        )
        self.tag = Tag.objects.create(name='Breakfast', slug='breakfast')
        self.ingredient = Ingredient.objects.create(
            name='Egg',
            measurement_unit='piece'
        )
        self.recipe = Recipe.objects.create(
            name='Test Recipe',
            author=self.user,
            cook_time=10
        )
        self.recipe.tags.add(self.tag)
        self.client.force_authenticate(user=self.user)

    def test_create_recipe(self):
        """
        Тестирование создания нового рецепта.

        Проверяет:
        - Успешное создание рецепта (201 Created)
        - Увеличение общего количества рецептов
        """
        url = reverse('recipe-list')
        data = {
            'name': 'New Recipe',
            'tags': [self.tag.id],
            'ingredients': [{'id': self.ingredient.id, 'amount': 2}],
            'cook_time': 15
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Recipe.objects.count(), 2)

    def test_add_to_favorite(self):
        """
        Тестирование добавления рецепта в избранное.

        Проверяет:
        - Успешное добавление (201 Created)
        - Наличие записи в базе данных
        """
        url = reverse('recipe-favorite', args=[self.recipe.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Favorite.objects.filter(
            user=self.user,
            recipe=self.recipe
        ).exists())


class ShoppingCartViewSetTests(APITestCase):
    """Набор тестов для работы с корзиной покупок."""

    def setUp(self):
        """Инициализация тестовых данных для корзины покупок."""
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpass'
        )
        self.recipe = Recipe.objects.create(
            name='Test Recipe',
            author=self.user,
            cook_time=10
        )
        ShoppingCart.objects.create(user=self.user, recipe=self.recipe)
        self.client.force_authenticate(user=self.user)

    def test_download_shopping_cart_txt(self):
        """
        Тестирование скачивания списка покупок в TXT формате.

        Проверяет:
        - Статус ответа 200 OK
        - Корректный Content-Type
        """
        url = reverse('shoppingcart-download-shopping-cart')
        response = self.client.get(url, {'format': 'txt'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/plain')

    def test_download_shopping_cart_pdf(self):
        """
        Тестирование скачивания списка покупок в PDF формате.

        Проверяет:
        - Статус ответа 200 OK
        - Корректный Content-Type
        """
        url = reverse('shoppingcart-download-shopping-cart')
        response = self.client.get(url, {'format': 'pdf'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/pdf')
