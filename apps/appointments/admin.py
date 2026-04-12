from django.contrib import admin
from django.utils.html import format_html
from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient_name', 'veterinarian', 'branch', 'scheduled_at',
                    'appointment_type', 'status_badge', 'is_today')
    list_filter = ('status', 'appointment_type', 'branch', 'veterinarian')
    search_fields = ('patient__name', 'patient__owner__phone',
                     'veterinarian__last_name', 'reason')
    readonly_fields = ('created_at', 'updated_at', 'reminder_24h_sent', 'reminder_1h_sent')
    raw_id_fields = ('patient', 'veterinarian', 'created_by')
    date_hierarchy = 'scheduled_at'
    ordering = ('scheduled_at',)

    fieldsets = (
        ('Appointment', {
            'fields': ('patient', 'veterinarian', 'branch',
                       ('scheduled_at', 'duration_minutes'),
                       ('appointment_type', 'status')),
        }),
        ('Notes', {
            'fields': ('reason', 'internal_notes'),
        }),
        ('Reminders', {
            'fields': ('reminder_24h_sent', 'reminder_1h_sent'),
            'classes': ('collapse',),
        }),
        ('Meta', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Patient')
    def patient_name(self, obj):
        return f"{obj.patient.species_emoji} {obj.patient.name}"

    @admin.display(description='Status')
    def status_badge(self, obj):
        colours = {
            'BOOKED': 'blue', 'CONFIRMED': 'teal', 'CHECKED_IN': 'purple',
            'IN_PROGRESS': 'orange', 'COMPLETED': 'green',
            'NO_SHOW': 'red', 'CANCELLED': 'grey',
        }
        return format_html(
            '<span style="color:{};font-weight:bold">{}</span>',
            colours.get(obj.status, 'grey'),
            obj.get_status_display(),
        )

    @admin.display(description='Today?', boolean=True)
    def is_today(self, obj):
        return obj.is_today
