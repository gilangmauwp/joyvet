"""
Core middleware:
  AuditMiddleware  — injects request user/IP into thread-local for audit logging
  TimezoneMiddleware — activates WIB timezone for authenticated users
"""
import threading
import zoneinfo
from typing import Callable

from django.http import HttpRequest, HttpResponse
from django.utils import timezone

_thread_locals = threading.local()


def get_current_user():
    """Return the User making the current request (or None for system tasks)."""
    return getattr(_thread_locals, 'user', None)


def get_current_ip() -> str | None:
    """Return the IP address of the current request."""
    return getattr(_thread_locals, 'ip', None)


class AuditMiddleware:
    """Store request user + IP in thread-local for AuditLog creation."""

    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        _thread_locals.user = getattr(request, 'user', None)
        _thread_locals.ip = self._get_client_ip(request)
        response = self.get_response(request)
        return response

    @staticmethod
    def _get_client_ip(request: HttpRequest) -> str | None:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


class TimezoneMiddleware:
    """
    Activate WIB (Asia/Jakarta) timezone for all authenticated requests
    so that timezone.localtime() returns WIB without extra conversion.
    """

    WIB = zoneinfo.ZoneInfo('Asia/Jakarta')

    def __init__(self, get_response: Callable) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.user.is_authenticated:
            timezone.activate(self.WIB)
        else:
            timezone.deactivate()
        return self.get_response(request)
