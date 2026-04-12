"""Template context injected into every rendered page."""
import zoneinfo
from django.conf import settings
from django.utils import timezone


def clinic_context(request) -> dict:
    wib = zoneinfo.ZoneInfo('Asia/Jakarta')
    now_wib = timezone.now().astimezone(wib)

    ctx: dict = {
        'CLINIC_NAME': settings.CLINIC_NAME,
        'CLINIC_CURRENCY': settings.CLINIC_CURRENCY,
        'now_wib': now_wib,
        'today_wib': now_wib.date(),
    }

    if request.user.is_authenticated:
        try:
            profile = request.user.staff_profile
            ctx['staff_profile'] = profile
            ctx['user_branch'] = profile.branch
            ctx['can_view_financials'] = profile.can_view_financials
            ctx['can_finalize'] = profile.can_finalize_records
        except Exception:
            ctx['staff_profile'] = None
            ctx['user_branch'] = None
            ctx['can_view_financials'] = False
            ctx['can_finalize'] = False

        # Low-stock alert count for nav badge
        from apps.inventory.models import InventoryItem
        branch = ctx.get('user_branch')
        if branch:
            ctx['low_stock_count'] = InventoryItem.objects.filter(
                branch=branch,
                is_active=True,
                stock_quantity__lte=models_reorder_level_expr(),
            ).count()

    return ctx


def models_reorder_level_expr():
    """Return a Q-compatible expression for low stock check."""
    from django.db.models import F
    return F('reorder_level')
