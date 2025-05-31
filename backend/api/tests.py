import base64

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework.authtoken.models import Token
from django.test import override_settings
from PIL import Image
from io import BytesIO

from users.models import Subscription
from recipes.models import (
    Ingredient, Tag, Recipe, RecipeIngredient, RecipeTags,
    Favorite, ShoppingCart
)
from utils.constants import PAGE_SIZE

User = get_user_model()


class TestSettingsMixin:
    def setUp(self):
        super().setUp()
        self.settings = override_settings(
            REST_FRAMEWORK={
                'DEFAULT_PAGINATION_CLASS': 'api.pagination.CustomPagination',
                'PAGE_SIZE': PAGE_SIZE
            }
        )
        self.settings.enable()
        
    def tearDown(self):
        self.settings.disable()
        super().tearDown()


class UserAPITests(APITestCase, TestSettingsMixin):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpassword',
            first_name='Test',
            last_name='User'
        )
        self.other_user = User.objects.create_user(
            email='other@example.com',
            username='otheruser',
            password='otherpassword'
        )
        self.client = APIClient()

    def test_user_registration(self):
        url = reverse('api:user-list')
        data = {
            'email': 'new@example.com',
            'username': 'newuser',
            'password': 'newpassword123',
            'first_name': 'New',
            'last_name': 'User'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 3)
        self.assertEqual(response.data['email'], 'new@example.com')
        self.assertNotIn('password', response.data)

    def test_get_current_user(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('api:user-me')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], self.user.email)

    def test_set_password(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('api:user-set-password')
        data = {
            'current_password': 'testpassword',
            'new_password': 'newtestpassword'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newtestpassword'))

    def test_subscribe(self):
        self.client.force_authenticate(user=self.user)
        url = reverse('api:users-subscribe', kwargs={'pk': self.other_user.id})
        
        # Подписаться
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Subscription.objects.filter(
            user=self.user, author=self.other_user).exists())
        
        # Отписаться
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Subscription.objects.filter(
            user=self.user, author=self.other_user).exists())


class AuthAPITests(APITestCase, TestSettingsMixin):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            email='test@example.com',
            username='testuser',
            password='testpassword'
        )
        self.client = APIClient()

    def test_token_obtain(self):
        # Используем фактический путь из urls.py
        url = '/api/auth/token/login/'
        data = {
            'email': 'test@example.com',
            'password': 'testpassword'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('auth_token', response.data)

    def test_token_logout(self):
        token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        # Используем фактический путь из urls.py
        url = '/api/auth/token/logout/'
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Token.objects.filter(user=self.user).exists())


class RecipeAPITests(APITestCase, TestSettingsMixin):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            email='chef@example.com',
            username='chef',
            password='chefpassword'
        )
        self.other_user = User.objects.create_user(
            email='other@example.com',
            username='other',
            password='otherpassword'
        )
        
        # Создаем ингредиенты
        self.ingredient1 = Ingredient.objects.create(
            name='Flour',
            measurement_unit='g'
        )
        self.ingredient2 = Ingredient.objects.create(
            name='Sugar',
            measurement_unit='g'
        )
        
        # Создаем теги
        self.tag1 = Tag.objects.create(name='Breakfast', slug='breakfast')
        self.tag2 = Tag.objects.create(name='Dessert', slug='dessert')
        
        # Создаем рецепт
        self.recipe = Recipe.objects.create(
            author=self.user,
            name='Pancakes',
            text='Delicious pancakes recipe',
            cooking_time=30
        )
        RecipeTags.objects.create(recipe=self.recipe, tag=self.tag1)
        RecipeIngredient.objects.create(
            recipe=self.recipe,
            ingredient=self.ingredient1,
            amount=200
        )
        
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def create_test_image_base64(self):
        """Создает валидное тестовое изображение в base64"""
        image = BytesIO()
        Image.new('RGB', (100, 100)).save(image, 'JPEG')
        image.seek(0)
        return f"data:image/jpeg;base64,{base64.b64encode(image.getvalue()).decode('utf-8')}"

    def test_create_recipe(self):
        url = reverse('api:recipes-list')
        data = {
            'name': 'New Recipe',
            'text': 'Description of new recipe',
            'cooking_time': 20,
            'tags': [self.tag1.id, self.tag2.id],
            'ingredients': [
                {'id': self.ingredient1.id, 'amount': 150},
                {'id': self.ingredient2.id, 'amount': 50}
            ],
            'image': self.create_test_image_base64()
        }
        response = self.client.post(url, data, format='json')
        
        if response.status_code != status.HTTP_201_CREATED:
            print("Ошибка создания рецепта:", response.data)
            
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Recipe.objects.count(), 2)

    def test_update_recipe(self):
        url = reverse('api:recipes-detail', kwargs={'pk': self.recipe.id})
        data = {
            'name': 'Updated Pancakes',
            'text': 'Updated description',
            'cooking_time': 25,
            'tags': [self.tag2.id],
            'ingredients': [{'id': self.ingredient2.id, 'amount': 100}]
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.recipe.refresh_from_db()
        self.assertEqual(self.recipe.name, 'Updated Pancakes')
        self.assertEqual(self.recipe.tags.count(), 1)
        self.assertEqual(self.recipe.ingredient_list.count(), 1)
        self.assertEqual(self.recipe.ingredient_list.first().ingredient, self.ingredient2)

    def test_delete_recipe(self):
        url = reverse('api:recipes-detail', kwargs={'pk': self.recipe.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Recipe.objects.count(), 0)

    def test_add_to_favorites(self):
        url = reverse('api:recipes-favorite', kwargs={'pk': self.recipe.id})
        
        # Добавить в избранное
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(Favorite.objects.filter(
            user=self.user, recipe=self.recipe).exists())
        
        # Удалить из избранного
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Favorite.objects.filter(
            user=self.user, recipe=self.recipe).exists())

    def test_add_to_shopping_cart(self):
        url = reverse('api:recipes-shopping-cart', kwargs={'pk': self.recipe.id})
        
        # Добавить в корзину
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(ShoppingCart.objects.filter(
            user=self.user, recipe=self.recipe).exists())
        
        # Удалить из корзины
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ShoppingCart.objects.filter(
            user=self.user, recipe=self.recipe).exists())

    def test_download_shopping_cart(self):
        # Добавляем рецепт в корзину
        ShoppingCart.objects.create(user=self.user, recipe=self.recipe)
        
        url = reverse('api:recipes-download-shopping-cart')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/plain')
        content = response.content.decode()
        self.assertIn('Flour', content)
        self.assertIn('200', content)

    def test_get_recipe_short_link(self):
        url = reverse('api:recipes-get-link', kwargs={'pk': self.recipe.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('short_link', response.data)
        self.assertTrue(response.data['short_link'].startswith('http'))


class IngredientTagAPITests(APITestCase, TestSettingsMixin):
    def setUp(self):
        super().setUp()
        self.ingredient1 = Ingredient.objects.create(
            name='Salt',
            measurement_unit='g'
        )
        self.ingredient2 = Ingredient.objects.create(
            name='Pepper',
            measurement_unit='g'
        )
        self.tag = Tag.objects.create(name='Spicy', slug='spicy')
        self.client = APIClient()

    def test_ingredient_list(self):
        url = reverse('api:ingredients-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # Проверяем наличие обоих ингредиентов
        ingredient_names = [i['name'] for i in response.data]
        self.assertIn('Salt', ingredient_names)
        self.assertIn('Pepper', ingredient_names)

    def test_ingredient_filter(self):
        url = reverse('api:ingredients-list') + '?name=salt'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Salt')

    def test_tag_list(self):
        url = reverse('api:tags-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['name'], 'Spicy')

    def test_tag_detail(self):
        url = reverse('api:tags-detail', kwargs={'pk': self.tag.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Spicy')


class FilterTests(APITestCase, TestSettingsMixin):
    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            email='chef@example.com',
            username='chef',
            password='chefpassword'
        )
        
        # Создаем ингредиенты
        self.flour = Ingredient.objects.create(name='Flour', measurement_unit='g')
        self.sugar = Ingredient.objects.create(name='Sugar', measurement_unit='g')
        
        # Создаем теги
        self.breakfast_tag = Tag.objects.create(name='Breakfast', slug='breakfast')
        self.dessert_tag = Tag.objects.create(name='Dessert', slug='dessert')
        
        # Создаем рецепты
        self.recipe1 = Recipe.objects.create(
            author=self.user,
            name='Pancakes',
            text='Breakfast pancakes',
            cooking_time=15
        )
        self.recipe1.tags.add(self.breakfast_tag)
        RecipeIngredient.objects.create(
            recipe=self.recipe1,
            ingredient=self.flour,
            amount=200
        )
        
        self.recipe2 = Recipe.objects.create(
            author=self.user,
            name='Cake',
            text='Delicious cake',
            cooking_time=60
        )
        self.recipe2.tags.add(self.dessert_tag)
        RecipeIngredient.objects.create(
            recipe=self.recipe2,
            ingredient=self.sugar,
            amount=100
        )
        
        self.client = APIClient()

    def get_results(self, response):
        """Возвращает результаты независимо от формата ответа"""
        if isinstance(response.data, dict) and 'results' in response.data:
            return response.data['results']
        return response.data

    def test_filter_by_tag(self):
        url = reverse('api:recipes-list') + f'?tags={self.breakfast_tag.slug}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = self.get_results(response)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], 'Pancakes')

    def test_filter_by_author(self):
        url = reverse('api:recipes-list') + f'?author={self.user.id}'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = self.get_results(response)
        self.assertEqual(len(results), 2)

    def test_filter_favorites(self):
        # Авторизуем пользователя и добавляем рецепт в избранное
        self.client.force_authenticate(user=self.user)
        Favorite.objects.create(user=self.user, recipe=self.recipe1)
        
        url = reverse('api:recipes-list') + '?is_favorited=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = self.get_results(response)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['name'], 'Pancakes')
