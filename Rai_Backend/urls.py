from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)
from rest_framework.permissions import AllowAny
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
    path('api/comments/', include('comment_concern.urls')),
    path('api/comment-concern/', include('comment_concern.urls')),
    path('api/notifications/', include('notifications.urls')),
    path('api/pages/', include('dashboard.pages_urls')),

    # API Documentation (Swagger & ReDoc)
    path('api/schema/', SpectacularAPIView.as_view(permission_classes=[AllowAny]), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema', permission_classes=[AllowAny]), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema', permission_classes=[AllowAny]), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)