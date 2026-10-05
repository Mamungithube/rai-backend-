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
import base64
import secrets
from functools import wraps
from django.http import HttpResponse, JsonResponse
from django.db import connection
import logging

logger = logging.getLogger(__name__)


def docs_basic_auth(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        expected_user = getattr(settings, 'DOCS_USERNAME', 'Admin')
        expected_pass = getattr(settings, 'DOCS_PASSWORD', 'password')

        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if auth_header.startswith('Basic '):
            try:
                auth_decoded = base64.b64decode(auth_header[6:]).decode('utf-8')
                username, password = auth_decoded.split(':', 1)
                if secrets.compare_digest(username, expected_user) and secrets.compare_digest(password, expected_pass):
                    return view_func(request, *args, **kwargs)
            except Exception:
                pass

        response = HttpResponse(
            "Unauthorized: Access to API documentation requires valid credentials.\n",
            status=401,
            content_type="text/plain"
        )
        response['WWW-Authenticate'] = 'Basic realm="Rai API Documentation"'
        return response
    return _wrapped_view


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

    # Protected API Documentation (HTTP Basic Auth)
    path('api/schema/', docs_basic_auth(SpectacularAPIView.as_view(permission_classes=[AllowAny])), name='schema'),
    path('api/docs/', docs_basic_auth(SpectacularSwaggerView.as_view(url_name='schema', permission_classes=[AllowAny])), name='swagger-ui'),
    path('api/redoc/', docs_basic_auth(SpectacularRedocView.as_view(url_name='schema', permission_classes=[AllowAny])), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)