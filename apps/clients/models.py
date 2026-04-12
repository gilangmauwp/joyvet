"""
Client models — the pet owner who pays and communicates.
"""
from django.db import models


class Client(models.Model):
    """Pet owner — the paying customer."""

    PREFERRED_CONTACT = [
        ('WA',    'WhatsApp'),
        ('SMS',   'SMS'),
        ('EMAIL', 'Email'),
        ('PHONE', 'Phone Call'),
    ]

    branch = models.ForeignKey(
        'core.Branch', on_delete=models.PROTECT, related_name='clients',
    )
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    whatsapp = models.CharField(
        max_length=20, blank=True,
        help_text="WhatsApp number if different from phone",
    )
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    id_number = models.CharField(
        max_length=20, blank=True,
        help_text="KTP / Passport number",
    )
    preferred_contact = models.CharField(
        max_length=10, choices=PREFERRED_CONTACT, default='WA',
    )
    notes = models.TextField(
        blank=True,
        help_text="VIP notes, preferences, allergies to communicate",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['last_name', 'first_name']
        verbose_name = 'Client'
        verbose_name_plural = 'Clients'
        unique_together = [('branch', 'phone')]
        indexes = [
            models.Index(fields=['phone']),
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['branch', 'is_active']),
        ]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.phone})"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def contact_number(self) -> str:
        """Return the best number for outbound messages."""
        return self.whatsapp or self.phone

    def to_search_dict(self) -> dict:
        """Lightweight dict for global search results."""
        return {
            'id': self.pk,
            'type': 'client',
            'name': self.full_name,
            'phone': self.phone,
            'branch': str(self.branch),
            'pet_count': self.pets.filter(is_active=True).count(),
        }
