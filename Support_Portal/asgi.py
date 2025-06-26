import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import Freewheel_Portal.routing  # Your app routing

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Support_Portal.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            Freewheel_Portal.routing.websocket_urlpatterns
        )
    ),
})
