"""
Core models — Branch, StaffProfile, AuditLog.
These are the foundation referenced by all other apps.
"""
from django.db import models
from django.contrib.auth.models import User


class Branch(models.Model):
    """A physical clinic location (JoyVet Care or JoyTails)."""

    name = models.CharField(max_length=100)
    code = models.CharField(
        max_length=5, unique=True,
        help_text="Short code used in invoice numbers, e.g. JVC or JTL",
    )
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Branch'
        verbose_name_plural = 'Branches'

    def __str__(self) -> str:
        return self.name


class StaffProfile(models.Model):
    """Extends Django User with clinic-specific fields."""

    ROLES = [
        ('OWNER',         'Owner'),
        ('VET',           'Veterinarian'),
        ('NURSE',         'Vet Nurse'),
        ('RECEPTIONIST',  'Receptionist'),
        ('GROOMER',       'Groomer'),
        ('INTERN',        'Intern'),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='staff_profile',
    )
    branch = models.ForeignKey(
        Branch, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='staff',
    )
    role = models.CharField(max_length=20, choices=ROLES)
    phone = models.CharField(max_length=20, blank=True)
    # 6-digit PIN for quick tablet unlock (stored hashed — see save())
    pin_code = models.CharField(max_length=128, blank=True)
    can_finalize_records = models.BooleanField(default=False)
    can_view_financials = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['user__last_name', 'user__first_name']
        verbose_name = 'Staff Profile'
        verbose_name_plural = 'Staff Profiles'

    def __str__(self) -> str:
        return f"{self.user.get_full_name()} ({self.get_role_display()})"

    @property
    def full_name(self) -> str:
        return self.user.get_full_name()


class AuditLog(models.Model):
    """
    Immutable audit trail — NEVER delete these records.
    Every write operation (create/update/delete) should produce one entry.
    """

    ACTIONS = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete'),
        ('LOGIN',  'Login'),
        ('LOGOUT', 'Logout'),
        ('FINALIZE', 'Finalize Record'),
        ('VOID',   'Void Invoice'),
    ]

    user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='audit_logs',
    )
    action = models.CharField(max_length=20, choices=ACTIONS)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    object_repr = models.CharField(max_length=300, blank=True)
    changes = models.JSONField(
        default=dict,
        help_text="Dict of {field: [old_value, new_value]}",
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'
        indexes = [
            models.Index(fields=['model_name', 'object_id']),
            models.Index(fields=['user', 'timestamp']),
        ]

    def __str__(self) -> str:
        user_str = self.user.get_full_name() if self.user else 'System'
        return f"[{self.timestamp:%Y-%m-%d %H:%M}] {user_str} {self.action} {self.model_name}#{self.object_id}"
