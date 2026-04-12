"""
Billing / POS models — Invoice, InvoiceLineItem.
Stock deducted on PAID transition only (prevents ghost deductions on voids).
Invoice number format: INV-{BRANCH_CODE}-{YYYYMM}-{SEQ:04d}
"""
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.utils import timezone


def generate_invoice_number(branch) -> str:
    """
    Thread-safe invoice number generation using SELECT FOR UPDATE.
    Format: INV-JVC-202406-0001
    """
    branch_code = (branch.code or branch.name[:3]).upper()
    month_str = timezone.now().strftime('%Y%m')
    prefix = f"INV-{branch_code}-{month_str}-"

    with transaction.atomic():
        last = (
            Invoice.objects.select_for_update()
            .filter(invoice_number__startswith=prefix)
            .order_by('-invoice_number')
            .first()
        )
        seq = 1
        if last:
            try:
                seq = int(last.invoice_number.split('-')[-1]) + 1
            except (ValueError, IndexError):
                seq = 1
        return f"{prefix}{seq:04d}"


class Invoice(models.Model):
    """
    Financial record for a consultation.
    Created automatically when a consultation is finalized.
    """

    STATUS = [
        ('DRAFT',   'Draft'),
        ('PENDING', 'Pending Payment'),
        ('PAID',    'Paid'),
        ('PARTIAL', 'Partially Paid'),
        ('VOID',    'Void / Cancelled'),
    ]
    PAYMENT_METHODS = [
        ('CASH',     'Cash'),
        ('QRIS',     'QRIS'),
        ('TRANSFER', 'Bank Transfer'),
        ('CARD',     'Debit / Credit Card'),
        ('SPLIT',    'Split Payment'),
    ]

    consultation = models.OneToOneField(
        'emr.Consultation', on_delete=models.PROTECT, related_name='invoice',
    )
    branch = models.ForeignKey(
        'core.Branch', on_delete=models.PROTECT, related_name='invoices',
    )
    invoice_number = models.CharField(max_length=50, unique=True)

    status = models.CharField(max_length=10, choices=STATUS, default='DRAFT')

    # All monetary values in IDR (Decimal, 0 decimal places)
    subtotal = models.DecimalField(
        max_digits=14, decimal_places=0, default=Decimal('0'),
    )
    discount_amount = models.DecimalField(
        max_digits=14, decimal_places=0, default=Decimal('0'),
    )
    tax_amount = models.DecimalField(
        max_digits=14, decimal_places=0, default=Decimal('0'),
    )
    total_amount = models.DecimalField(
        max_digits=14, decimal_places=0, default=Decimal('0'),
    )
    paid_amount = models.DecimalField(
        max_digits=14, decimal_places=0, default=Decimal('0'),
    )

    payment_method = models.CharField(
        max_length=10, choices=PAYMENT_METHODS, blank=True,
    )
    payment_reference = models.CharField(
        max_length=100, blank=True,
        help_text="Bank transfer ref, QRIS transaction ID, card last 4",
    )
    notes = models.TextField(blank=True)

    created_by = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name='invoices_created',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'
        indexes = [
            models.Index(fields=['status', 'branch']),
            models.Index(fields=['created_at']),
            models.Index(fields=['invoice_number']),
        ]

    def __str__(self) -> str:
        return f"{self.invoice_number} — {self.get_status_display()} — Rp {self.total_amount:,.0f}"

    def save(self, *args, **kwargs) -> None:
        if not self.invoice_number:
            self.invoice_number = generate_invoice_number(self.branch)
        super().save(*args, **kwargs)

    def recalculate_totals(self) -> None:
        """Recompute subtotal, tax, and total from line items."""
        items = self.items.all()
        subtotal = sum(item.subtotal for item in items)
        tax = sum(
            item.subtotal * (item.inventory_item.tax_rate / 100)
            for item in items
        )
        self.subtotal = Decimal(subtotal).quantize(Decimal('1'))
        self.tax_amount = Decimal(tax).quantize(Decimal('1'))
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
        self.save(update_fields=['subtotal', 'tax_amount', 'total_amount', 'updated_at'])

    @property
    def balance_due(self) -> Decimal:
        return max(self.total_amount - self.paid_amount, Decimal('0'))

    @property
    def patient(self):
        return self.consultation.patient


class InvoiceLineItem(models.Model):
    """One line on an invoice — a service, medicine, or retail item."""

    invoice = models.ForeignKey(
        Invoice, on_delete=models.CASCADE, related_name='items',
    )
    inventory_item = models.ForeignKey(
        'inventory.InventoryItem', on_delete=models.PROTECT,
    )
    description = models.CharField(
        max_length=300, help_text="Auto-filled from item name; editable",
    )
    quantity = models.DecimalField(
        max_digits=8, decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    unit_price = models.DecimalField(
        max_digits=14, decimal_places=0,
        help_text="Price at time of sale — snapshot, not live",
    )
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0'),
    )
    subtotal = models.DecimalField(max_digits=14, decimal_places=0)

    class Meta:
        ordering = ['id']
        verbose_name = 'Invoice Line Item'
        verbose_name_plural = 'Invoice Line Items'

    def __str__(self) -> str:
        return f"{self.description} × {self.quantity} @ Rp {self.unit_price:,.0f}"

    def save(self, *args, **kwargs) -> None:
        # Auto-compute subtotal with discount
        gross = self.unit_price * self.quantity
        discount = gross * (self.discount_percent / 100)
        self.subtotal = (gross - discount).quantize(Decimal('1'))
        if not self.description:
            self.description = self.inventory_item.name
        super().save(*args, **kwargs)
