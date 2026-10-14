from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AdminPageSettingsViewSet

router = DefaultRouter()
router.register(r'', AdminPageSettingsViewSet, basename='public-pages')

urlpatterns = [
    path('', include(router.urls)),
]
