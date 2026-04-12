"""WebSocket URL routing — referenced from joyvet/asgi.py."""
from django.urls import re_path
from .consumers import ClinicConsumer, ConsultationConsumer

websocket_urlpatterns = [
    re_path(r'^ws/clinic/$', ClinicConsumer.as_asgi()),
    re_path(r'^ws/consultation/(?P<pk>\d+)/$', ConsultationConsumer.as_asgi()),
]
