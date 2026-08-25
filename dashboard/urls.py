from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AdminUserViewSet, 
    AdminCommunityViewSet, 
    AdminSupportViewSet, 
    AdminPageSettingsViewSet
)

router = DefaultRouter()
router.register(r'users', AdminUserViewSet, basename='admin-users')
router.register(r'communities', AdminCommunityViewSet, basename='admin-communities')
router.register(r'support', AdminSupportViewSet, basename='admin-support')
router.register(r'pages', AdminPageSettingsViewSet, basename='admin-pages')

urlpatterns = [
    path('', include(router.urls)),
]