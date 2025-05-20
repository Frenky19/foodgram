from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path
from drf_yasg import openapi
from drf_yasg.views import get_schema_view

schema_view = get_schema_view(
    openapi.Info(
        title='Foodgram',
        default_version='',
    ),
    public=True,
)

urlpatterns = [
    path('api/', include('api.urls')),
    path('admin/', admin.site.urls),
    path('redoc/', schema_view.with_ui('redoc'), name='redoc'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
