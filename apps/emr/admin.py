from django.contrib import admin
from django.utils.html import format_html
from .models import Consultation, MedicalAttachment, Prescription


class AttachmentInline(admin.TabularInline):
    model = MedicalAttachment
    extra = 0
    fields = ('file_type', 'description', 'file', 'uploaded_by', 'uploaded_at')
    readonly_fields = ('uploaded_at', 'uploaded_by')


class PrescriptionInline(admin.TabularInline):
    model = Prescription
    extra = 0
    fields = ('inventory_item', 'dosage', 'frequency', 'duration_days',
              'quantity', 'is_controlled_drug')


@admin.register(Consultation)
class ConsultationAdmin(admin.ModelAdmin):
    list_display = ('patient_link', 'visiting_vet', 'visit_date', 'status_badge',
                    'branch', 'finalized_at')
    list_filter = ('status', 'branch', 'visit_date')
    search_fields = ('patient__name', 'attending_vet__last_name',
                     'assessment', 'patient__owner__phone')
    readonly_fields = ('status', 'finalized_by', 'finalized_at', 'version',
                       'created_at', 'updated_at')
    raw_id_fields = ('patient', 'attending_vet', 'appointment')
    date_hierarchy = 'visit_date'
    inlines = [PrescriptionInline, AttachmentInline]

    fieldsets = (
        ('Visit', {
            'fields': ('patient', 'attending_vet', 'branch', 'visit_date', 'appointment'),
        }),
        ('SOAP Notes', {
            'fields': ('subjective', 'objective', 'assessment', 'plan'),
        }),
        ('Vitals', {
            'fields': (('temperature_celsius', 'heart_rate_bpm', 'respiratory_rate'),
                       ('weight_kg', 'capillary_refill_time', 'mucous_membrane_color')),
            'classes': ('collapse',),
        }),
        ('Follow-up & Internal', {
            'fields': ('follow_up_date', 'internal_notes'),
            'classes': ('collapse',),
        }),
        ('Record Status', {
            'fields': ('status', 'version', 'finalized_by', 'finalized_at'),
        }),
    )

    @admin.display(description='Patient')
    def patient_link(self, obj):
        return format_html('<a href="#">{}</a>', obj.patient.name)

    @admin.display(description='Vet')
    def visiting_vet(self, obj):
        return obj.attending_vet.get_full_name()

    @admin.display(description='Status')
    def status_badge(self, obj):
        colours = {'OPEN': 'blue', 'CLOSED': 'green', 'CANCELLED': 'red'}
        colour = colours.get(obj.status, 'grey')
        return format_html(
            '<span style="color:{};font-weight:bold">{}</span>',
            colour, obj.get_status_display()
        )

    def has_delete_permission(self, request, obj=None):
        # Closed records should never be deleted
        if obj and obj.status == 'CLOSED':
            return False
        return super().has_delete_permission(request, obj)
