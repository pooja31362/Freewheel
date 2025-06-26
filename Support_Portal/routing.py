# your_project_name/routing.py

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import Freewheel_Portal.routing

application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter(
            Freewheel_Portal.routing.websocket_urlpatterns
        )
    ),
})
