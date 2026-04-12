"""
EMR models — Consultation (SOAP), MedicalAttachment, Prescription.
Records are mutable while OPEN; immutable once CLOSED (finalized).
"""
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Consultation(models.Model):
    """
    The core EMR record.  One record per visit.
    Uses SOAP note structure (Subjective / Objective / Assessment / Plan).
    Immutable after finalization — triggers invoice creation via signal.
    """

    STATUS = [
        ('OPEN',      'Open — editing allowed'),
        ('CLOSED',    'Closed — read only'),
        ('CANCELLED', 'Cancelled'),
    ]

    patient = models.ForeignKey(
        'patients.Patient', on_delete=models.CASCADE, related_name='visits',
    )
    attending_vet = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='consultations',
    )
    branch = models.ForeignKey(
        'core.Branch', on_delete=models.PROTECT, related_name='consultations',
    )
    visit_date = models.DateTimeField(default=timezone.now)
    appointment = models.OneToOneField(
        'appointments.Appointment', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='consultation',
    )

    # ── SOAP Notes ───────────────────────────────────────
    subjective = models.TextField(
        blank=True, help_text="Owner complaint, history, presenting signs",
    )
    objective = models.TextField(
        blank=True, help_text="Vitals, physical exam findings",
    )
    assessment = models.TextField(
        blank=True, help_text="Diagnosis / differential diagnoses",
    )
    plan = models.TextField(
        blank=True, help_text="Treatment plan, prescriptions, follow-up instructions",
    )

    # ── Vitals (stored for charting) ──────────────────────
    temperature_celsius = models.DecimalField(
        max_digits=4, decimal_places=1, null=True, blank=True,
    )
    heart_rate_bpm = models.IntegerField(null=True, blank=True)
    respiratory_rate = models.IntegerField(null=True, blank=True)
    weight_kg = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
    )
    capillary_refill_time = models.CharField(max_length=20, blank=True)
    mucous_membrane_color = models.CharField(max_length=50, blank=True)

    # ── Concurrency & immutability ─────────────────────────
    status = models.CharField(max_length=20, choices=STATUS, default='OPEN')
    version = models.IntegerField(
        default=1,
        help_text="Optimistic locking — increment on every save to detect conflicts",
    )
    finalized_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='finalized_consultations',
    )
    finalized_at = models.DateTimeField(null=True, blank=True)

    follow_up_date = models.DateField(null=True, blank=True)
    internal_notes = models.TextField(
        blank=True, help_text="Staff-only notes — not visible to client",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-visit_date']
        verbose_name = 'Consultation'
        verbose_name_plural = 'Consultations'
        indexes = [
            models.Index(fields=['patient', 'visit_date']),
            models.Index(fields=['branch', 'status']),
            models.Index(fields=['attending_vet', 'visit_date']),
        ]

    def __str__(self) -> str:
        return (
            f"[{self.get_status_display()}] "
            f"{self.patient.name} — {self.visit_date:%Y-%m-%d} "
            f"(Dr. {self.attending_vet.last_name})"
        )

    def finalize(self, user: User) -> None:
        """
        Lock this record permanently.
        Irreversible. Fires signal that auto-creates the Invoice.
        """
        if self.status == 'CLOSED':
            raise ValueError("Consultation is already finalized.")
        if self.status == 'CANCELLED':
            raise ValueError("Cancelled consultations cannot be finalized.")
        self.status = 'CLOSED'
        self.finalized_by = user
        self.finalized_at = timezone.now()
        self.version += 1
        self.save(update_fields=['status', 'finalized_by', 'finalized_at', 'version', 'updated_at'])


class MedicalAttachment(models.Model):
    """
    Files attached to a consultation — photos, lab results, X-rays.
    Supports multi-device upload (tablet camera, desktop file upload).
    """

    TYPES = [
        ('PHOTO', 'Clinical Photo'),
        ('LAB',   'Lab Result'),
        ('XRAY',  'X-Ray / DICOM'),
        ('DOC',   'Document'),
        ('VIDEO', 'Video'),
    ]

    consultation = models.ForeignKey(
        Consultation, on_delete=models.CASCADE, related_name='attachments',
    )
    file = models.FileField(upload_to='emr/%Y/%m/%d/')
    file_type = models.CharField(max_length=10, choices=TYPES)
    description = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    source_device = models.CharField(
        max_length=50, blank=True,
        help_text="X-Device-ID header — useful for multi-device audit",
    )
    is_from_camera = models.BooleanField(
        default=False, help_text="True when captured directly from device camera",
    )

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Medical Attachment'
        verbose_name_plural = 'Medical Attachments'

    def __str__(self) -> str:
        return f"{self.get_file_type_display()} for {self.consultation} by {self.uploaded_by}"


class Prescription(models.Model):
    """
    A prescribed medication tied to a consultation.
    Links EMR → Inventory for stock deduction on invoice payment.
    Controlled drugs require a witnessed signature.
    """

    consultation = models.ForeignKey(
        Consultation, on_delete=models.CASCADE, related_name='prescriptions',
    )
    inventory_item = models.ForeignKey(
        'inventory.InventoryItem', on_delete=models.PROTECT,
        related_name='prescriptions',
    )
    dosage = models.CharField(
        max_length=200, help_text="e.g. 5mg/kg, 1 tablet",
    )
    frequency = models.CharField(
        max_length=100, help_text="e.g. Twice daily, Every 8 hours",
    )
    duration_days = models.IntegerField()
    quantity = models.DecimalField(
        max_digits=8, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    notes = models.CharField(max_length=500, blank=True)
    is_controlled_drug = models.BooleanField(default=False)
    # Controlled drug: requires a second staff member to witness
    witnessed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='witnessed_prescriptions',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Prescription'
        verbose_name_plural = 'Prescriptions'

    def __str__(self) -> str:
        return (
            f"{self.inventory_item.name} × {self.quantity} "
            f"— {self.dosage} {self.frequency}"
        )
