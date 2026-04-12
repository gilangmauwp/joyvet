from django.contrib import admin
from django.utils.html import format_html
from .models import Patient, WeightRecord, VaccinationRecord


class WeightInline(admin.TabularInline):
    model = WeightRecord
    extra = 0
    fields = ('weight_kg', 'recorded_at', 'recorded_by', 'notes')
    readonly_fields = ('recorded_at',)
    ordering = ('-recorded_at',)
    max_num = 10
    show_change_link = True


class VaccinationInline(admin.TabularInline):
    model = VaccinationRecord
    extra = 0
    fields = ('vaccine_name', 'administered_date', 'next_due_date', 'is_overdue_display')
    readonly_fields = ('is_overdue_display',)
    ordering = ('-administered_date',)

    @admin.display(description='Overdue?')
    def is_overdue_display(self, obj):
        if obj.is_overdue:
            return format_html('<span style="color:red">⚠ Overdue</span>')
        return format_html('<span style="color:green">✓ Current</span>')


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ('name', 'species_display', 'breed', 'owner', 'current_weight_kg',
                    'is_active', 'is_deceased')
    list_filter = ('species', 'gender', 'is_active', 'is_deceased', 'owner__branch')
    search_fields = ('name', 'microchip_number', 'owner__first_name', 'owner__last_name',
                     'owner__phone')
    readonly_fields = ('qr_code_preview', 'created_at', 'updated_at')
    raw_id_fields = ('owner',)
    inlines = [WeightInline, VaccinationInline]

    fieldsets = (
        ('Identity', {
            'fields': ('owner', ('name', 'species', 'breed'), ('gender', 'birth_date'),
                       'microchip_number', 'photo'),
        }),
        ('Health', {
            'fields': ('current_weight_kg', 'known_allergies'),
        }),
        ('Insurance', {
            'fields': (('insurance_provider', 'insurance_number'),),
            'classes': ('collapse',),
        }),
        ('Status', {
            'fields': (('is_active', 'is_deceased'), 'qr_code_preview'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Species')
    def species_display(self, obj):
        return f"{obj.species_emoji} {obj.get_species_display()}"

    @admin.display(description='QR Code')
    def qr_code_preview(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="120" />', obj.qr_code.url)
        return '—'


@admin.register(WeightRecord)
class WeightRecordAdmin(admin.ModelAdmin):
    list_display = ('patient', 'weight_kg', 'recorded_at', 'recorded_by')
    list_filter = ('patient__species',)
    search_fields = ('patient__name',)
    date_hierarchy = 'recorded_at'


@admin.register(VaccinationRecord)
class VaccinationRecordAdmin(admin.ModelAdmin):
    list_display = ('patient', 'vaccine_name', 'administered_date',
                    'next_due_date', 'overdue_status')
    list_filter = ('vaccine_name',)
    search_fields = ('patient__name', 'vaccine_name', 'batch_number')
    date_hierarchy = 'administered_date'

    @admin.display(description='Status')
    def overdue_status(self, obj):
        if obj.is_overdue:
            return format_html('<span style="color:red">⚠ Overdue</span>')
        days = obj.days_until_due
        if days <= 30:
            return format_html('<span style="color:orange">Due in {} days</span>', days)
        return format_html('<span style="color:green">✓</span>')
