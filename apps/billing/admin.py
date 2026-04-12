from django.contrib import admin
from django.utils.html import format_html
from .models import Invoice, InvoiceLineItem


class LineItemInline(admin.TabularInline):
    model = InvoiceLineItem
    extra = 0
    fields = ('inventory_item', 'description', 'quantity', 'unit_price',
              'discount_percent', 'subtotal')
    readonly_fields = ('subtotal',)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'patient_name', 'branch', 'status_badge',
                    'total_display', 'payment_method', 'created_at', 'paid_at')
    list_filter = ('status', 'branch', 'payment_method')
    search_fields = ('invoice_number', 'consultation__patient__name',
                     'consultation__patient__owner__phone')
    readonly_fields = ('invoice_number', 'created_at', 'updated_at', 'paid_at')
    raw_id_fields = ('consultation', 'created_by')
    date_hierarchy = 'created_at'
    inlines = [LineItemInline]

    fieldsets = (
        ('Invoice', {
            'fields': ('invoice_number', 'consultation', 'branch', 'status'),
        }),
        ('Amounts (IDR)', {
            'fields': (('subtotal', 'discount_amount'), ('tax_amount', 'total_amount'),
                       ('paid_amount', 'payment_method', 'payment_reference')),
        }),
        ('Meta', {
            'fields': ('notes', 'created_by', 'created_at', 'paid_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Patient')
    def patient_name(self, obj):
        return obj.consultation.patient.name

    @admin.display(description='Status')
    def status_badge(self, obj):
        colours = {
            'DRAFT': 'grey', 'PENDING': 'blue', 'PAID': 'green',
            'PARTIAL': 'orange', 'VOID': 'red',
        }
        return format_html(
            '<span style="color:{};font-weight:bold">{}</span>',
            colours.get(obj.status, 'grey'),
            obj.get_status_display(),
        )

    @admin.display(description='Total')
    def total_display(self, obj):
        return f"Rp {int(obj.total_amount):,}".replace(',', '.')
