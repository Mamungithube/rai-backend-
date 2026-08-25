from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import BettingViewSet

router = DefaultRouter()
router.register(r'', BettingViewSet, basename='betting')

urlpatterns =[
    path('', include(router.urls)),
]