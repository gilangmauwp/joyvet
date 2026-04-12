"""
Inventory models — medicines, vaccines, supplies, retail items.
Stock movements are the source of truth for Pandas forecasting.
"""
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class InventoryItem(models.Model):
    """A stockable item — medicine, vaccine, supply, food, or service."""

    CATEGORY = [
        ('MED',      'Medicine'),
        ('VACCINE',  'Vaccine'),
        ('SUPPLY',   'Medical Supply'),
        ('FOOD',     'Pet Food'),
        ('GROOMING', 'Grooming Product'),
        ('RETAIL',   'Retail Item'),
        ('SERVICE',  'Service (non-stock)'),
    ]

    branch = models.ForeignKey(
        'core.Branch', on_delete=models.PROTECT, related_name='inventory',
    )
    name = models.CharField(max_length=200)
    generic_name = models.CharField(
        max_length=200, blank=True,
        help_text="Generic / INN name for medicines",
    )
    category = models.CharField(max_length=10, choices=CATEGORY)
    sku = models.CharField(max_length=50, unique=True)
    barcode = models.CharField(max_length=100, blank=True, db_index=True)
    unit = models.CharField(
        max_length=20, default='unit',
        help_text="e.g. tablet, ml, bottle, bag",
    )

    # Pricing — ALL in IDR, always Decimal
    cost_price = models.DecimalField(
        max_digits=14, decimal_places=0,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Purchase/cost price in IDR",
    )
    selling_price = models.DecimalField(
        max_digits=14, decimal_places=0,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Retail selling price in IDR",
    )
    tax_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal('0'),
        help_text="Tax percentage e.g. 11.00 for 11% PPN",
    )

    # Stock
    stock_quantity = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0'),
    )
    reorder_level = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('5'),
        help_text="Trigger low-stock alert when quantity drops to this level",
    )
    max_stock = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
    )

    # Expiry & batch
    expiry_date = models.DateField(null=True, blank=True)
    batch_number = models.CharField(max_length=50, blank=True)

    # Flags
    is_controlled_drug = models.BooleanField(
        default=False,
        help_text="Requires witnessed prescription and double-check",
    )
    is_active = models.BooleanField(default=True)
    requires_prescription = models.BooleanField(default=False)

    # Pandas forecasting fields — updated nightly by Celery task
    avg_daily_consumption = models.DecimalField(
        max_digits=8, decimal_places=3, null=True, blank=True,
    )
    predicted_stockout_date = models.DateField(null=True, blank=True)
    restock_recommendation = models.IntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'name']
        verbose_name = 'Inventory Item'
        verbose_name_plural = 'Inventory Items'
        indexes = [
            models.Index(fields=['branch', 'category', 'is_active']),
            models.Index(fields=['sku']),
            models.Index(fields=['expiry_date']),
        ]

    def __str__(self) -> str:
        return f"{self.name} [{self.sku}]"

    @property
    def is_low_stock(self) -> bool:
        return self.stock_quantity <= self.reorder_level

    @property
    def is_out_of_stock(self) -> bool:
        return self.stock_quantity <= 0

    @property
    def days_until_expiry(self) -> int | None:
        if not self.expiry_date:
            return None
        return (self.expiry_date - timezone.now().date()).days

    @property
    def margin_percent(self) -> Decimal:
        if self.cost_price <= 0:
            return Decimal('0')
        return ((self.selling_price - self.cost_price) / self.cost_price * 100).quantize(
            Decimal('0.1')
        )


class StockTransaction(models.Model):
    """
    Every stock movement in or out.
    The authoritative ledger used by Pandas forecasting.
    Positive quantity = stock in, negative = stock out.
    """

    TYPES = [
        ('PURCHASE',   'Purchase / Received'),
        ('SALE',       'Sold via Invoice'),
        ('ADJUSTMENT', 'Manual Adjustment'),
        ('EXPIRED',    'Expired / Disposed'),
        ('RETURN',     'Client Return'),
        ('TRANSFER',   'Branch Transfer'),
        ('VACCINE_USE','Used in Vaccination'),
    ]

    item = models.ForeignKey(
        InventoryItem, on_delete=models.PROTECT, related_name='transactions',
    )
    transaction_type = models.CharField(max_length=20, choices=TYPES)
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2,
        help_text="Positive = in, Negative = out",
    )
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    reference_id = models.CharField(
        max_length=100, blank=True,
        help_text="Invoice number, PO number, or adjustment ID",
    )
    performed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
    )
    notes = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Stock Transaction'
        verbose_name_plural = 'Stock Transactions'
        indexes = [
            models.Index(fields=['item', 'transaction_type', 'created_at']),
        ]

    def __str__(self) -> str:
        direction = '+' if self.quantity > 0 else ''
        return (
            f"{self.item.name}: {direction}{self.quantity} "
            f"({self.get_transaction_type_display()}) → balance {self.balance_after}"
        )
