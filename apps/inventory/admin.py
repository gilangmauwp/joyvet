from django.contrib import admin
from django.utils.html import format_html
from .models import InventoryItem, StockTransaction


class StockTransactionInline(admin.TabularInline):
    model = StockTransaction
    extra = 0
    fields = ('transaction_type', 'quantity', 'balance_after', 'reference_id',
              'performed_by', 'created_at')
    readonly_fields = ('balance_after', 'created_at')
    ordering = ('-created_at',)
    max_num = 20


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'branch', 'stock_status',
                    'selling_price_display', 'expiry_status', 'is_active')
    list_filter = ('category', 'branch', 'is_controlled_drug', 'is_active',
                   'requires_prescription')
    search_fields = ('name', 'generic_name', 'sku', 'barcode')
    readonly_fields = ('avg_daily_consumption', 'predicted_stockout_date',
                       'restock_recommendation', 'created_at', 'updated_at')
    inlines = [StockTransactionInline]
    ordering = ('category', 'name')

    fieldsets = (
        ('Product', {
            'fields': (('name', 'generic_name'), ('category', 'unit'),
                       ('sku', 'barcode'), 'branch'),
        }),
        ('Pricing (IDR)', {
            'fields': (('cost_price', 'selling_price'), 'tax_rate'),
        }),
        ('Stock', {
            'fields': (('stock_quantity', 'reorder_level', 'max_stock'),
                       ('expiry_date', 'batch_number')),
        }),
        ('Flags', {
            'fields': (('is_controlled_drug', 'requires_prescription', 'is_active'),),
        }),
        ('Forecasting (Auto-updated nightly)', {
            'fields': ('avg_daily_consumption', 'predicted_stockout_date',
                       'restock_recommendation'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Stock')
    def stock_status(self, obj):
        qty = obj.stock_quantity
        if obj.is_out_of_stock:
            return format_html('<span style="color:red;font-weight:bold">OUT: {}</span>', qty)
        if obj.is_low_stock:
            return format_html('<span style="color:orange">LOW: {}</span>', qty)
        return format_html('<span style="color:green">{}</span>', qty)

    @admin.display(description='Selling Price')
    def selling_price_display(self, obj):
        return f"Rp {int(obj.selling_price):,}".replace(',', '.')

    @admin.display(description='Expiry')
    def expiry_status(self, obj):
        days = obj.days_until_expiry
        if days is None:
            return '—'
        if days < 0:
            return format_html('<span style="color:red">EXPIRED</span>')
        if days <= 30:
            return format_html('<span style="color:orange">{} days</span>', days)
        return format_html('<span style="color:green">{} days</span>', days)


@admin.register(StockTransaction)
class StockTransactionAdmin(admin.ModelAdmin):
    list_display = ('item', 'transaction_type', 'quantity', 'balance_after',
                    'reference_id', 'performed_by', 'created_at')
    list_filter = ('transaction_type', 'item__branch')
    search_fields = ('item__name', 'reference_id')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

    def has_change_permission(self, request, obj=None):
        return False  # Ledger entries are immutable
