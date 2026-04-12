"""
Pandas-based inventory demand forecasting.
Uses exponential weighted moving average on 90-day consumption history.
Updates InventoryItem forecasting fields nightly via Celery.
"""
from __future__ import annotations
import logging
from datetime import date, timedelta

import pandas as pd
from django.utils import timezone

logger = logging.getLogger(__name__)


def predict_stockout(item_id: int) -> dict:
    """
    Forecast stockout date and reorder quantity for a single inventory item.

    Algorithm:
      1. Fetch 90 days of SALE transactions
      2. Resample to daily consumption series (fill gaps with 0)
      3. Apply 14-day EWMA to weight recent consumption more heavily
      4. Project days remaining from current stock
      5. Recommend 30-day supply + 20% safety buffer

    Returns a dict with status + forecast fields.
    """
    from apps.inventory.models import InventoryItem, StockTransaction

    transactions = list(
        StockTransaction.objects.filter(
            item_id=item_id,
            transaction_type='SALE',
            created_at__gte=timezone.now() - timedelta(days=90),
        ).values('created_at', 'quantity')
    )

    if not transactions:
        logger.debug('No transactions for item %s — skipping forecast', item_id)
        return {'status': 'insufficient_data'}

    df = pd.DataFrame(transactions)
    df['created_at'] = pd.to_datetime(df['created_at'], utc=True)
    df['quantity'] = df['quantity'].abs()

    # Daily consumption series
    daily = (
        df.set_index('created_at')
        .resample('D')['quantity']
        .sum()
        .fillna(0)
    )

    # EWMA with 14-day span — weights recent demand higher
    ewma = daily.ewm(span=14, adjust=False).mean()
    avg_daily = float(ewma.iloc[-1])

    try:
        item = InventoryItem.objects.get(pk=item_id)
    except InventoryItem.DoesNotExist:
        return {'status': 'item_not_found'}

    current_stock = float(item.stock_quantity)

    if avg_daily <= 0:
        # Save zero-consumption status
        InventoryItem.objects.filter(pk=item_id).update(
            avg_daily_consumption=0,
            predicted_stockout_date=None,
            restock_recommendation=None,
        )
        return {'status': 'no_consumption', 'item_id': item_id, 'avg_daily': 0}

    days_remaining = int(current_stock / avg_daily)
    stockout_date = date.today() + timedelta(days=days_remaining)

    # 30-day supply + 20% safety stock, rounded to nearest unit
    recommended_order = max(1, int((avg_daily * 30) * 1.2))

    InventoryItem.objects.filter(pk=item_id).update(
        avg_daily_consumption=round(avg_daily, 3),
        predicted_stockout_date=stockout_date,
        restock_recommendation=recommended_order,
    )

    return {
        'status': 'ok',
        'item_id': item_id,
        'avg_daily_consumption': round(avg_daily, 3),
        'days_remaining': days_remaining,
        'predicted_stockout': stockout_date.isoformat(),
        'recommended_order_qty': recommended_order,
    }
