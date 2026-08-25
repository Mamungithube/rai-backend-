from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework.permissions import IsAdminUser
from rest_framework.authentication import SessionAuthentication
from django.http import JsonResponse
from django.db import connection
import logging

logger = logging.getLogger(__name__)


def health_check(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({
            "status": "healthy",
            "database": "connected",
            "version": "1.0.0"
        })
    except Exception as e:
        logger.error("health_check_failed", error=str(e), exc_info=True)
        return JsonResponse({
            "status": "unhealthy",
            "error": "Service unavailable. Please try again later."
        }, status=503)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('authentication.urls')),
    path('api/ai/', include('ai.urls')),
    path('api/community/', include('community.urls')),
    path('api/support/', include('support.urls')),
    path('api/dashboard/', include('dashboard.urls')),
    path('api/health/', health_check, name='health-check'),
    path('api/betting/', include('betting.urls')),
]

if settings.DEBUG:
    urlpatterns += [
        path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
        path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
urlpatterns += [
    path('api/schema/', SpectacularAPIView.as_view(
        permission_classes=[IsAdminUser]
    ), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(
        url_name='schema',
        permission_classes=[IsAdminUser]
    ), name='swagger-ui'),
]