"""
Patient Celery tasks — vaccination due-date reminders.
"""
import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task
def send_vaccination_reminders() -> dict:
    """
    Remind owners of upcoming vaccinations (7-day window).
    Runs daily at 08:00 WIB.
    """
    from apps.patients.models import VaccinationRecord

    today = timezone.now().date()
    due_soon = VaccinationRecord.objects.filter(
        next_due_date__range=[today, today + timedelta(days=7)],
        reminder_sent=False,
        patient__is_active=True,
    ).select_related(
        'patient', 'patient__owner', 'patient__owner__branch'
    )

    sent = 0
    for vacc in due_soon:
        owner = vacc.patient.owner
        if owner.preferred_contact not in ('WA', 'SMS'):
            continue

        days = vacc.days_until_due
        message = (
            f"*JoyVet Care Vaccination Reminder*\n\n"
            f"Hi {owner.first_name}! 🐾\n\n"
            f"*{vacc.patient.name}'s* {vacc.vaccine_name} vaccination is due "
            f"{'today' if days == 0 else f'in {days} day(s)'}!\n\n"
            f"Please call or book online to schedule.\n\n"
            f"{vacc.patient.owner.branch.name}\n"
            f"📞 {vacc.patient.owner.branch.phone}"
        )

        try:
            from apps.appointments.tasks import _dispatch_whatsapp
            _dispatch_whatsapp(owner.contact_number, message)
            vacc.reminder_sent = True
            vacc.save(update_fields=['reminder_sent'])
            sent += 1
        except Exception as e:
            logger.error('Vaccination reminder failed for %s: %s', vacc.pk, e)

    logger.info('Vaccination reminders sent: %d', sent)
    return {'sent': sent}
