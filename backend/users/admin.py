from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html

from users.models import Subscription

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Управление пользователями системы в административном интерфейсе."""

    list_display = (
        'username', 'avatar_preview', 'first_name',
        'last_name', 'email'
    )
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    readonly_fields = ('avatar_preview', 'date_joined', 'last_login')
    search_fields = ('username', 'email', 'first_name', 'last_name')

    def avatar_preview(self, obj):
        """Отображает изображения профиля пользователя в админке.

        Возвращает:
            HTML-тег изображения, если файл существует, или текст-заглушку.
        """
        if obj.avatar:
            return format_html(
                ('<img src="{}" style="max-height:'
                 '100px; max-width: 100px;" />'),
                obj.avatar.url
            )
        return 'Нет изображения'
    avatar_preview.short_description = 'Фото профиля'


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """Управление подписками пользователей в административном интерфейсе."""

    list_display = ('user', 'author')
    list_filter = ('user', 'author')
    search_fields = (
        'user__username',
        'user__email',
        'user__first_name',
        'user__last_name',
        'author__username',
        'author__email',
        'author__first_name',
        'author__last_name'
    )
    autocomplete_fields = ('user', 'author')

    def get_queryset(self, request):
        """Оптимизированные запросы с предзагрузкой связанных объектов."""
        return super().get_queryset(request).select_related('user', 'author')
