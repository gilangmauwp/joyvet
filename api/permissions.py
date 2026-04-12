"""
Custom DRF permissions for JoyVet Care.
"""
from rest_framework.permissions import BasePermission, SAFE_METHODS


class IsStaffMember(BasePermission):
    """User must have a StaffProfile (any role)."""

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and hasattr(request.user, 'staff_profile')
        )


class CanViewFinancials(BasePermission):
    """Only users with can_view_financials flag can see invoice/revenue data."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        try:
            return request.user.staff_profile.can_view_financials
        except Exception:
            return False


class CanFinalizeRecords(BasePermission):
    """Only vets/owners with can_finalize_records can close consultations."""

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        try:
            return request.user.staff_profile.can_finalize_records
        except Exception:
            return False


class IsSameBranch(BasePermission):
    """Object-level: user can only access records from their own branch."""

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True
        try:
            user_branch = request.user.staff_profile.branch
        except Exception:
            return False

        # Support branch directly on obj or via related field
        obj_branch = getattr(obj, 'branch', None) or getattr(
            getattr(obj, 'patient', None), 'owner', None
        )
        if obj_branch is None:
            return True
        return obj_branch == user_branch


class ReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS
