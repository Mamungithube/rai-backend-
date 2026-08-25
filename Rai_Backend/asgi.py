import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Rai_Backend.settings')
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from authentication.middleware import JWTAuthMiddleware
from ai import routing as ai_routing
from community import routing as community_routing

django_asgi_app = get_asgi_application()

websocket_urlpatterns = ai_routing.websocket_urlpatterns + community_routing.websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": JWTAuthMiddleware(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})