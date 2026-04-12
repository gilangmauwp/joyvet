from django.contrib import admin
from django.utils.html import format_html
from .models import Branch, StaffProfile, AuditLog


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'phone', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'code', 'phone')
    ordering = ('name',)


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'role_display', 'branch', 'can_finalize_records',
                    'can_view_financials', 'is_active')
    list_filter = ('role', 'branch', 'can_finalize_records', 'is_active')
    search_fields = ('user__first_name', 'user__last_name', 'user__email')
    raw_id_fields = ('user', 'branch')
    readonly_fields = ('created_at',)

    @admin.display(description='Name')
    def full_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    @admin.display(description='Role')
    def role_display(self, obj):
        return obj.get_role_display()


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'model_name', 'object_id',
                    'ip_address')
    list_filter = ('action', 'model_name')
    search_fields = ('user__username', 'model_name', 'object_id', 'object_repr')
    readonly_fields = ('user', 'action', 'model_name', 'object_id', 'object_repr',
                       'changes', 'ip_address', 'timestamp')
    date_hierarchy = 'timestamp'
    ordering = ('-timestamp',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
