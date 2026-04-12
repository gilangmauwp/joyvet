"""
Core utilities used across all apps.
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from django.contrib.auth.models import User
    from django.http import HttpRequest


def write_audit_log(
    *,
    user: 'User | None',
    action: str,
    model_name: str,
    object_id: str,
    object_repr: str = '',
    changes: dict | None = None,
    request: 'HttpRequest | None' = None,
    ip_address: str | None = None,
) -> None:
    """
    Create an AuditLog entry.
    Safe to call from signals, views, and Celery tasks.
    """
    from apps.core.models import AuditLog
    from apps.core.middleware import get_current_ip

    resolved_ip = ip_address or (
        _get_request_ip(request) if request else get_current_ip()
    )

    AuditLog.objects.create(
        user=user,
        action=action,
        model_name=model_name,
        object_id=str(object_id),
        object_repr=object_repr,
        changes=changes or {},
        ip_address=resolved_ip,
    )


def _get_request_ip(request: 'HttpRequest') -> str | None:
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def format_idr(amount) -> str:
    """Format a Decimal as Indonesian Rupiah: Rp 1.250.000"""
    try:
        return f"Rp {int(amount):,}".replace(',', '.')
    except (TypeError, ValueError):
        return 'Rp 0'


def notify_branch_ws(branch_id: int, event_type: str, data: dict) -> None:
    """
    Send a WebSocket message to all devices connected in a branch.
    Safe to call from synchronous code (Celery tasks, views, signals).
    """
    from channels.layers import get_channel_layer
    from asgiref.sync import async_to_sync

    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f'clinic_{branch_id}',
        {'type': event_type.replace('.', '_'), **data},
    )
