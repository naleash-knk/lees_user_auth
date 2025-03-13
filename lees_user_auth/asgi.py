import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
# import your websocket routing if you have it
# from chat import routing  # Or music.routing if using WebSockets

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lees_user_auth.settings')

# Django's ASGI application for HTTP
django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter({
    "http": django_asgi_app,  # ✅ Handles HTTP requests
    "websocket": AuthMiddlewareStack(  # ✅ Handles WebSocket connections
         URLRouter(
            routing.websocket_urlpatterns  # your websocket routes here
        )
    )
})
