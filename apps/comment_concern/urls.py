from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CommentConcernViewSet

router = DefaultRouter()
router.register(r'', CommentConcernViewSet, basename='comment-concern')

urlpatterns = [
    path('', include(router.urls)),
]
