from django.urls import include, path
from rest_framework.routers import DefaultRouter

from api.views import IngredientViewSet, RecipeViewSet, TagViewSet, UserViewSet

app_name = 'api'

router = DefaultRouter()

router.register('users', UserViewSet, 'users')
router.register('ingredients', IngredientViewSet, 'ingredients')
router.register('recipes', RecipeViewSet, 'recipes')
router.register('tags', TagViewSet, 'tags')

urlpatterns = [
    path('', include(router.urls)),
    path(
        'users/me/avatar/',
        UserViewSet.as_view({'put': 'avatar', 'delete': 'delete_avatar'}),
        name='user-avatar'
    ),
    path('auth/', include('djoser.urls.authtoken')),
    path('', include('djoser.urls'))
]
