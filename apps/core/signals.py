"""
Core signals — audit log creation on auth events.
Model-level audit logs are written from the billing/emr signal files.
"""
from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from apps.core.utils import write_audit_log


@receiver(user_logged_in)
def log_login(sender, request, user, **kwargs) -> None:
    write_audit_log(
        user=user,
        action='LOGIN',
        model_name='User',
        object_id=str(user.pk),
        object_repr=user.get_full_name() or user.username,
        request=request,
    )


@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs) -> None:
    if user:
        write_audit_log(
            user=user,
            action='LOGOUT',
            model_name='User',
            object_id=str(user.pk),
            object_repr=user.get_full_name() or user.username,
            request=request,
        )


@receiver(user_login_failed)
def log_login_failed(sender, credentials, request, **kwargs) -> None:
    from apps.core.models import AuditLog
    from apps.core.middleware import get_current_ip
    AuditLog.objects.create(
        user=None,
        action='LOGIN',
        model_name='User',
        object_id='',
        object_repr=f"FAILED: {credentials.get('username', 'unknown')}",
        changes={'error': 'Login failed'},
        ip_address=get_current_ip(),
    )
