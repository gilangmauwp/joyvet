"""
Patient models — the animals receiving care.
"""
from __future__ import annotations
from decimal import Decimal
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Patient(models.Model):
    """An animal patient. The clinical subject of all EMR records."""

    SPECIES = [
        ('DOG',     'Dog'),
        ('CAT',     'Cat'),
        ('RABBIT',  'Rabbit'),
        ('BIRD',    'Bird'),
        ('REPTILE', 'Reptile'),
        ('HAMSTER', 'Hamster'),
        ('EXOTIC',  'Exotic / Other'),
    ]
    GENDER = [
        ('M',  'Male'),
        ('F',  'Female'),
        ('MN', 'Male (Neutered)'),
        ('FS', 'Female (Spayed)'),
    ]
    SPECIES_EMOJI = {
        'DOG': '🐶', 'CAT': '🐱', 'RABBIT': '🐰',
        'BIRD': '🐦', 'REPTILE': '🦎', 'HAMSTER': '🐹', 'EXOTIC': '🐾',
    }

    owner = models.ForeignKey(
        'clients.Client', on_delete=models.CASCADE, related_name='pets',
    )
    name = models.CharField(max_length=100)
    species = models.CharField(max_length=10, choices=SPECIES)
    breed = models.CharField(max_length=100, blank=True)
    gender = models.CharField(max_length=2, choices=GENDER)
    birth_date = models.DateField(null=True, blank=True)
    microchip_number = models.CharField(max_length=50, blank=True, db_index=True)

    current_weight_kg = models.DecimalField(
        max_digits=6, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        default=Decimal('1.00'),
    )
    photo = models.ImageField(
        upload_to='patients/photos/%Y/%m/', blank=True,
    )
    # QR code auto-generated on first save — printed for kennel/cage
    qr_code = models.ImageField(upload_to='patients/qr/', blank=True)

    known_allergies = models.TextField(blank=True)
    insurance_provider = models.CharField(max_length=100, blank=True)
    insurance_number = models.CharField(max_length=50, blank=True)

    is_deceased = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Patient'
        verbose_name_plural = 'Patients'
        indexes = [
            models.Index(fields=['owner', 'is_active']),
            models.Index(fields=['species']),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_species_display()}) — {self.owner}"

    @property
    def species_emoji(self) -> str:
        return self.SPECIES_EMOJI.get(self.species, '🐾')

    @property
    def age_display(self) -> str:
        if not self.birth_date:
            return 'Unknown age'
        today = timezone.now().date()
        delta = today - self.birth_date
        years, remainder = divmod(delta.days, 365)
        months = remainder // 30
        if years > 0:
            return f"{years}y {months}m"
        return f"{months} months"

    def to_search_dict(self) -> dict:
        return {
            'id': self.pk,
            'type': 'patient',
            'name': self.name,
            'species': self.get_species_display(),
            'species_emoji': self.species_emoji,
            'breed': self.breed,
            'owner_name': self.owner.full_name,
            'owner_phone': self.owner.phone,
            'photo_url': self.photo.url if self.photo else None,
        }

    def save(self, *args, **kwargs) -> None:
        """Auto-generate QR code on first save."""
        is_new = self.pk is None
        if is_new:
            # Save first so we get a PK
            super().save(*args, **kwargs)
            self._generate_qr()
            # Update only qr_code field — avoid triggering signals again
            Patient.objects.filter(pk=self.pk).update(qr_code=self.qr_code)
        else:
            if not self.qr_code:
                self._generate_qr()
            super().save(*args, **kwargs)

    def _generate_qr(self) -> None:
        """Create a QR code PNG encoding the patient identifier."""
        import qrcode  # type: ignore

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(f"JOYVET:PATIENT:{self.pk}:{self.name}")
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='white')

        buffer = BytesIO()
        img.save(buffer, format='PNG')
        filename = f"patient_{self.pk}_qr.png"
        self.qr_code.save(filename, ContentFile(buffer.getvalue()), save=False)


class WeightRecord(models.Model):
    """Weight history for growth charting and drug dosage tracking."""

    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name='weight_history',
    )
    weight_kg = models.DecimalField(
        max_digits=6, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    recorded_at = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
    )
    notes = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ['-recorded_at']
        verbose_name = 'Weight Record'
        verbose_name_plural = 'Weight Records'

    def __str__(self) -> str:
        return f"{self.patient.name}: {self.weight_kg} kg at {self.recorded_at:%Y-%m-%d}"


class VaccinationRecord(models.Model):
    """Vaccination history with auto-expiry tracking."""

    patient = models.ForeignKey(
        Patient, on_delete=models.CASCADE, related_name='vaccinations',
    )
    vaccine_name = models.CharField(max_length=200)
    batch_number = models.CharField(max_length=50, blank=True)
    administered_date = models.DateField()
    next_due_date = models.DateField()
    administered_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='vaccinations_given',
    )
    # Links to inventory so stock is auto-deducted
    inventory_item = models.ForeignKey(
        'inventory.InventoryItem', on_delete=models.SET_NULL, null=True, blank=True,
        help_text="Vaccine product — auto-deducts from stock when saved",
    )
    reminder_sent = models.BooleanField(default=False)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-administered_date']
        verbose_name = 'Vaccination Record'
        verbose_name_plural = 'Vaccination Records'

    def __str__(self) -> str:
        return f"{self.patient.name}: {self.vaccine_name} on {self.administered_date}"

    @property
    def is_overdue(self) -> bool:
        return self.next_due_date < timezone.now().date()

    @property
    def days_until_due(self) -> int:
        delta = self.next_due_date - timezone.now().date()
        return delta.days
