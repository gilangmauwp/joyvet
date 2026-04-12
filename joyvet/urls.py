"""
JoyVet Care — Root URL Configuration
  /          → HTMX server-rendered frontend
  /api/v1/   → Django REST Framework API
  /ws/       → WebSocket (Django Channels)
  /admin/    → Django admin
  /accounts/ → Django auth (login/logout)
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views

admin.site.site_header = 'JoyVet Care — Admin'
admin.site.site_title = 'JoyVet Care'
admin.site.index_title = 'Clinic Management'

urlpatterns = [
    # Django admin
    path('admin/', admin.site.urls),

    # Standard Django auth (login, logout, password reset)
    path('accounts/', include('django.contrib.auth.urls')),

    # REST API
    path('api/v1/', include('api.urls')),

    # WebSocket routes are handled by ASGI router in joyvet/asgi.py
    # (no HTTP URL needed)

    # HTMX server-rendered frontend — catch-all last
    path('', include('frontend.urls')),
]

# Serve media files via Django in dev (Nginx handles this in production)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
