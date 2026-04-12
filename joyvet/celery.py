"""
Celery application for JoyVet Care.
Handles: WhatsApp reminders, inventory forecasting,
         report generation, nightly backups.
"""
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'joyvet.settings.local')

app = Celery('joyvet')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# ── Periodic task schedule ─────────────────────────────────
app.conf.beat_schedule = {
    # Appointment reminders — every 30 minutes
    'appointment-reminders': {
        'task': 'apps.appointments.tasks.send_appointment_reminders',
        'schedule': crontab(minute='*/30'),
    },
    # Vaccination due-date reminders — daily at 08:00 WIB (01:00 UTC)
    'vaccination-reminders': {
        'task': 'apps.patients.tasks.send_vaccination_reminders',
        'schedule': crontab(hour=1, minute=0),
    },
    # Inventory forecasting — nightly at 02:00 WIB (19:00 UTC prev day)
    'inventory-forecasting': {
        'task': 'apps.analytics.tasks.run_all_forecasts',
        'schedule': crontab(hour=19, minute=0),
    },
    # Expiry alerts — daily at 08:30 WIB (01:30 UTC)
    'expiry-alerts': {
        'task': 'apps.inventory.tasks.check_expiry_alerts',
        'schedule': crontab(hour=1, minute=30),
    },
    # Daily revenue report — 07:00 WIB (00:00 UTC)
    'daily-revenue-report': {
        'task': 'apps.analytics.tasks.generate_daily_report',
        'schedule': crontab(hour=0, minute=0),
    },
}

app.conf.task_routes = {
    'apps.appointments.tasks.*': {'queue': 'reminders'},
    'apps.patients.tasks.*':     {'queue': 'reminders'},
    'apps.analytics.tasks.*':   {'queue': 'reports'},
    'apps.inventory.tasks.*':   {'queue': 'default'},
    'apps.billing.tasks.*':     {'queue': 'default'},
}
