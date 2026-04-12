"""
Appointment models — scheduling, status flow, reminders.
"""
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class Appointment(models.Model):
    """A scheduled visit. Drives the daily queue and reminder system."""

    STATUS = [
        ('BOOKED',      'Booked'),
        ('CONFIRMED',   'Confirmed'),
        ('CHECKED_IN',  'Checked In'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED',   'Completed'),
        ('NO_SHOW',     'No Show'),
        ('CANCELLED',   'Cancelled'),
    ]
    TYPES = [
        ('CONSULT',   'Consultation'),
        ('VACCINE',   'Vaccination'),
        ('GROOM',     'Grooming'),
        ('SURGERY',   'Surgery'),
        ('FOLLOWUP',  'Follow-up'),
        ('EMERGENCY', 'Emergency'),
        ('BOARDING',  'Boarding Check-in'),
    ]

    # Terminal statuses — no further transitions allowed
    TERMINAL_STATUSES = {'COMPLETED', 'NO_SHOW', 'CANCELLED'}
    # Statuses that block a vet timeslot
    ACTIVE_STATUSES = {'BOOKED', 'CONFIRMED', 'IN_PROGRESS'}

    patient = models.ForeignKey(
        'patients.Patient', on_delete=models.CASCADE, related_name='appointments',
    )
    veterinarian = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='appointments',
    )
    branch = models.ForeignKey(
        'core.Branch', on_delete=models.PROTECT, related_name='appointments',
    )
    scheduled_at = models.DateTimeField()
    duration_minutes = models.IntegerField(default=30)
    appointment_type = models.CharField(max_length=15, choices=TYPES)
    status = models.CharField(max_length=15, choices=STATUS, default='BOOKED')
    reason = models.TextField(blank=True)
    internal_notes = models.TextField(blank=True)

    # Reminder tracking (Celery tasks set these to avoid double-sending)
    reminder_24h_sent = models.BooleanField(default=False)
    reminder_1h_sent = models.BooleanField(default=False)

    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_appointments',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheduled_at']
        verbose_name = 'Appointment'
        verbose_name_plural = 'Appointments'
        indexes = [
            models.Index(fields=['branch', 'scheduled_at']),
            models.Index(fields=['veterinarian', 'scheduled_at']),
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['status']),
        ]
        constraints = [
            # Database-level: one vet cannot have two active bookings at same time
            models.UniqueConstraint(
                fields=['veterinarian', 'scheduled_at'],
                condition=models.Q(status__in=['BOOKED', 'CONFIRMED', 'IN_PROGRESS']),
                name='unique_vet_timeslot',
            ),
        ]

    def __str__(self) -> str:
        return (
            f"{self.patient.name} with {self.veterinarian.get_full_name()} "
            f"at {self.scheduled_at:%Y-%m-%d %H:%M}"
        )

    @property
    def is_today(self) -> bool:
        return self.scheduled_at.date() == timezone.now().date()

    @property
    def is_overdue(self) -> bool:
        return (
            self.scheduled_at < timezone.now()
            and self.status not in self.TERMINAL_STATUSES
        )

    def advance_status(self) -> str:
        """Return the next logical status for one-tap progression."""
        transitions = {
            'BOOKED':      'CHECKED_IN',
            'CONFIRMED':   'CHECKED_IN',
            'CHECKED_IN':  'IN_PROGRESS',
            'IN_PROGRESS': 'COMPLETED',
        }
        return transitions.get(self.status, self.status)
