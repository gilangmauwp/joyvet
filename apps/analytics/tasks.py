"""
Celery tasks for analytics — run nightly.
"""
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_forecast_for_item(self, item_id: int) -> dict:
    """Run stockout forecast for a single inventory item."""
    try:
        from apps.analytics.forecasting import predict_stockout
        return predict_stockout(item_id)
    except Exception as exc:
        logger.error('Forecast failed for item %s: %s', item_id, exc)
        raise self.retry(exc=exc)


@shared_task
def run_all_forecasts() -> dict:
    """
    Nightly: run forecasts for all active medicines/vaccines/supplies.
    Dispatched as individual tasks for parallel processing.
    """
    from apps.inventory.models import InventoryItem

    items = InventoryItem.objects.filter(
        is_active=True,
        category__in=['MED', 'VACCINE', 'SUPPLY'],
    ).values_list('id', flat=True)

    count = 0
    for item_id in items:
        run_forecast_for_item.delay(item_id)
        count += 1

    logger.info('Dispatched forecasts for %d items', count)
    return {'dispatched': count}


@shared_task
def generate_daily_report() -> None:
    """
    Generate and cache daily revenue report for all branches.
    Runs at 07:00 WIB (00:00 UTC).
    """
    from datetime import date
    from django.core.cache import cache
    from apps.core.models import Branch
    from apps.analytics.reports import revenue_report

    today = date.today()
    for branch in Branch.objects.filter(is_active=True):
        report = revenue_report(branch.pk, today, today)
        cache_key = f'daily_report_{branch.pk}_{today}'
        cache.set(cache_key, report, timeout=86400)

    logger.info('Daily reports generated for %s', today)
