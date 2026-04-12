"""
Business analytics using Pandas.
All financial figures in IDR (integer Decimals).
"""
from __future__ import annotations
import logging
from datetime import date, timedelta

try:
    import pandas as pd
    _PANDAS = True
except ImportError:
    _PANDAS = False

from django.db.models import Sum, Count, Avg

logger = logging.getLogger(__name__)


def revenue_report(branch_id: int, date_from: date, date_to: date) -> dict:
    """
    Returns a financial summary for a given branch and date range.
    Used by the analytics dashboard.
    """
    from apps.billing.models import Invoice

    invoices = list(
        Invoice.objects.filter(
            branch_id=branch_id,
            status='PAID',
            paid_at__date__range=[date_from, date_to],
        ).values('paid_at', 'payment_method', 'total_amount')
    )

    if not invoices:
        return {
            'total_revenue': 0,
            'transaction_count': 0,
            'avg_invoice_value': 0,
            'by_day': {},
            'by_payment_method': {},
        }

    if not _PANDAS:
        # Fallback: pure Python aggregation when pandas not installed
        total = sum(float(i['total_amount']) for i in invoices)
        by_day: dict = {}
        by_method: dict = {}
        for inv in invoices:
            day = str(inv['paid_at'].date() if hasattr(inv['paid_at'], 'date') else inv['paid_at'])
            by_day[day] = by_day.get(day, 0) + int(float(inv['total_amount']))
            m = inv['payment_method']
            by_method[m] = by_method.get(m, 0) + int(float(inv['total_amount']))
        return {
            'total_revenue': int(total),
            'transaction_count': len(invoices),
            'avg_invoice_value': int(total / len(invoices)),
            'by_day': by_day,
            'by_payment_method': by_method,
        }

    df = pd.DataFrame(invoices)
    df['paid_at'] = pd.to_datetime(df['paid_at'], utc=True).dt.date
    df['total_amount'] = df['total_amount'].astype(float)

    return {
        'total_revenue': int(df['total_amount'].sum()),
        'transaction_count': len(df),
        'avg_invoice_value': int(df['total_amount'].mean()),
        'by_day': {
            str(k): int(v)
            for k, v in df.groupby('paid_at')['total_amount'].sum().items()
        },
        'by_payment_method': {
            k: int(v)
            for k, v in df.groupby('payment_method')['total_amount'].sum().items()
        },
    }


def dashboard_stats(branch_id: int) -> dict:
    """
    Quick stats for the clinic dashboard:
    - Today's appointment counts by status
    - Today's revenue
    - Low stock count
    - Upcoming vaccinations due
    """
    from django.utils import timezone
    from apps.appointments.models import Appointment
    from apps.billing.models import Invoice
    from apps.inventory.models import InventoryItem
    from apps.patients.models import VaccinationRecord
    from django.db.models import F

    today = timezone.now().date()

    appt_qs = Appointment.objects.filter(branch_id=branch_id, scheduled_at__date=today)
    appt_stats = appt_qs.values('status').annotate(count=Count('id'))
    appt_by_status = {row['status']: row['count'] for row in appt_stats}

    revenue_today = Invoice.objects.filter(
        branch_id=branch_id, status='PAID', paid_at__date=today
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    low_stock_count = InventoryItem.objects.filter(
        branch_id=branch_id, is_active=True,
        stock_quantity__lte=F('reorder_level'),
    ).count()

    vaccs_due_soon = VaccinationRecord.objects.filter(
        patient__owner__branch_id=branch_id,
        next_due_date__range=[today, today + timedelta(days=30)],
        reminder_sent=False,
    ).count()

    return {
        'appointments_today': appt_by_status,
        'waiting': appt_by_status.get('CHECKED_IN', 0) + appt_by_status.get('BOOKED', 0),
        'in_progress': appt_by_status.get('IN_PROGRESS', 0),
        'completed_today': appt_by_status.get('COMPLETED', 0),
        'revenue_today': int(revenue_today),
        'low_stock_count': low_stock_count,
        'vaccinations_due_soon': vaccs_due_soon,
    }
