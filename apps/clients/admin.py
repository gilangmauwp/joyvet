from django.contrib import admin
from django.utils.html import format_html
from .models import Client


class PetInline(admin.TabularInline):
    from apps.patients.models import Patient
    model = Patient
    extra = 0
    fields = ('name', 'species', 'breed', 'gender', 'is_active')
    readonly_fields = ('name', 'species', 'breed', 'gender')
    show_change_link = True
    can_delete = False

    def get_queryset(self, request):
        return super().get_queryset(request).filter(is_active=True)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'phone', 'branch', 'preferred_contact',
                    'pet_count', 'created_at')
    list_filter = ('branch', 'preferred_contact', 'is_active')
    search_fields = ('first_name', 'last_name', 'phone', 'whatsapp', 'email',
                     'id_number')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('last_name', 'first_name')
    inlines = [PetInline]

    fieldsets = (
        ('Personal Information', {
            'fields': (('first_name', 'last_name'), ('phone', 'whatsapp'),
                       'email', 'id_number'),
        }),
        ('Communication', {
            'fields': ('preferred_contact', 'notes'),
        }),
        ('Clinic', {
            'fields': ('branch', 'is_active'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description='Name')
    def full_name(self, obj):
        return obj.full_name

    @admin.display(description='Pets')
    def pet_count(self, obj):
        n = obj.pets.filter(is_active=True).count()
        return format_html('<b>{}</b>', n)
