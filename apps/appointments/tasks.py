"""
Appointment Celery tasks — WhatsApp/SMS reminders.
Runs every 30 minutes via Celery Beat.
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def send_appointment_reminders() -> dict:
    """
    Sends two rounds of reminders:
    - 24-hour: the day before
    - 1-hour:  one hour before
    Marks flags to prevent duplicate sends.
    """
    from apps.appointments.models import Appointment

    now = timezone.now()
    stats = {'sent_24h': 0, 'sent_1h': 0, 'errors': 0}

    # 24-hour window: appointments between 23h and 25h from now
    window_24h_start = now + timedelta(hours=23)
    window_24h_end = now + timedelta(hours=25)

    appts_24h = Appointment.objects.filter(
        scheduled_at__range=(window_24h_start, window_24h_end),
        status__in=['BOOKED', 'CONFIRMED'],
        reminder_24h_sent=False,
    ).select_related('patient', 'patient__owner', 'veterinarian', 'branch')

    for appt in appts_24h:
        if _send_reminder(appt, '24h'):
            stats['sent_24h'] += 1
        else:
            stats['errors'] += 1
        appt.reminder_24h_sent = True
        appt.save(update_fields=['reminder_24h_sent'])

    # 1-hour window
    window_1h_start = now + timedelta(minutes=50)
    window_1h_end = now + timedelta(minutes=70)

    appts_1h = Appointment.objects.filter(
        scheduled_at__range=(window_1h_start, window_1h_end),
        status__in=['BOOKED', 'CONFIRMED', 'CHECKED_IN'],
        reminder_1h_sent=False,
    ).select_related('patient', 'patient__owner', 'veterinarian', 'branch')

    for appt in appts_1h:
        if _send_reminder(appt, '1h'):
            stats['sent_1h'] += 1
        else:
            stats['errors'] += 1
        appt.reminder_1h_sent = True
        appt.save(update_fields=['reminder_1h_sent'])

    logger.info('Reminders sent: %s', stats)
    return stats


def _send_reminder(appointment, reminder_type: str) -> bool:
    """Dispatch a single reminder via the configured WhatsApp provider."""
    owner = appointment.patient.owner
    if owner.preferred_contact not in ('WA', 'SMS'):
        return True  # Silently skip non-WhatsApp clients

    to_number = owner.contact_number
    if not to_number:
        return False

    template = (
        f"*JoyVet Care Reminder*\n\n"
        f"Hi {owner.first_name}! 👋\n\n"
        f"This is a reminder that *{appointment.patient.name}* has an appointment "
        f"with *Dr. {appointment.veterinarian.last_name}* at "
        f"*{appointment.branch.name}*.\n\n"
        f"📅 {appointment.scheduled_at.strftime('%A, %d %B %Y')}\n"
        f"⏰ {appointment.scheduled_at.strftime('%H:%M')} WIB\n"
        f"📋 {appointment.get_appointment_type_display()}\n\n"
        f"Please reply *CONFIRM* to confirm or *CANCEL* to cancel.\n"
        f"Thank you! 🐾"
    )

    try:
        _dispatch_whatsapp(to_number, template)
        return True
    except Exception as e:
        logger.error('WhatsApp send failed for appt %s: %s', appointment.pk, e)
        return False


def _dispatch_whatsapp(to: str, message: str) -> None:
    """
    Send via Twilio or 360dialog depending on WHATSAPP_PROVIDER setting.
    Gracefully no-ops if credentials are not configured (system works offline).
    """
    from django.conf import settings

    if not settings.WHATSAPP_ENABLED:
        logger.debug('WhatsApp not configured — skipping send to %s', to)
        return

    if settings.WHATSAPP_PROVIDER == 'twilio':
        _send_twilio(to, message)
    else:
        _send_360dialog(to, message)


def _send_twilio(to: str, message: str) -> None:
    from django.conf import settings
    from twilio.rest import Client  # type: ignore

    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    client.messages.create(
        from_=settings.TWILIO_WHATSAPP_FROM,
        to=f'whatsapp:{to}',
        body=message,
    )


def _send_360dialog(to: str, message: str) -> None:
    import requests
    from django.conf import settings

    requests.post(
        'https://waba.360dialog.io/v1/messages',
        json={'to': to, 'type': 'text', 'text': {'body': message}},
        headers={'D360-API-KEY': settings.DIALOG360_API_KEY},
        timeout=10,
    )
