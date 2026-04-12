"""
Inventory Celery tasks — low-stock alerts, expiry alerts.
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def send_low_stock_alert(item_id: int) -> None:
    """Notify branch staff of a low-stock item via WebSocket."""
    from apps.inventory.models import InventoryItem
    from apps.core.utils import notify_branch_ws

    try:
        item = InventoryItem.objects.select_related('branch').get(pk=item_id)
    except InventoryItem.DoesNotExist:
        return

    notify_branch_ws(
        branch_id=item.branch_id,
        event_type='inventory.low_stock',
        data={
            'item_id': item.pk,
            'item_name': item.name,
            'current_qty': str(item.stock_quantity),
            'reorder_level': str(item.reorder_level),
            'unit': item.unit,
        },
    )
    logger.info('Low-stock alert sent for %s (qty: %s)', item.name, item.stock_quantity)


@shared_task
def check_expiry_alerts() -> dict:
    """
    Check items expiring within alert thresholds (30, 60, 90 days).
    Runs daily at 08:30 WIB.
    """
    from datetime import date, timedelta
    from django.conf import settings
    from apps.inventory.models import InventoryItem
    from apps.core.utils import notify_branch_ws
    from apps.core.models import Branch

    today = date.today()
    alert_days = sorted(settings.EXPIRY_ALERT_DAYS)
    max_days = max(alert_days)

    expiring = InventoryItem.objects.filter(
        is_active=True,
        expiry_date__range=[today, today + timedelta(days=max_days)],
    ).select_related('branch')

    alerts_sent = 0
    for item in expiring:
        days = (item.expiry_date - today).days
        severity = 'critical' if days <= 30 else 'warning' if days <= 60 else 'info'
        notify_branch_ws(
            branch_id=item.branch_id,
            event_type='inventory.expiry_alert',
            data={
                'item_id': item.pk,
                'item_name': item.name,
                'expiry_date': item.expiry_date.isoformat(),
                'days_remaining': days,
                'severity': severity,
            },
        )
        alerts_sent += 1

    logger.info('Expiry alerts: %d items checked', alerts_sent)
    return {'alerts_sent': alerts_sent}
