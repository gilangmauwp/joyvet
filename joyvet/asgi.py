"""
ASGI config — handles both HTTP (Django) and WebSocket (Channels).
Run with: daphne -b 0.0.0.0 -p 8000 joyvet.asgi:application
"""
import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from django.urls import re_path

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'joyvet.settings.local')
django.setup()

# Import consumers AFTER django.setup()
from realtime.consumers import ClinicConsumer, ConsultationConsumer  # noqa: E402

django_asgi_app = get_asgi_application()

websocket_urlpatterns = [
    re_path(r'^ws/clinic/$', ClinicConsumer.as_asgi()),
    re_path(r'^ws/consultation/(?P<pk>\d+)/$', ConsultationConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})
