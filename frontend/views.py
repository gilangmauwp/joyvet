"""
HTMX server-rendered frontend views.
All views return full pages or HTML fragments for hx-swap.
"""
from __future__ import annotations
import json
import logging

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger(__name__)


# ── Global Search ──────────────────────────────────────────────────────────

class GlobalSearchView(APIView):
    """
    Unified search across patients, clients, microchips, phones.
    Called by HTMX search bar with hx-trigger="keyup changed delay:300ms".
    Returns JSON for Alpine.js dropdown — renders in < 50ms on LAN.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if len(query) < 2:
            return Response({'results': []})

        from apps.patients.models import Patient

        patients = (
            Patient.objects.filter(
                Q(name__icontains=query)
                | Q(microchip_number__iexact=query)
                | Q(owner__first_name__icontains=query)
                | Q(owner__last_name__icontains=query)
                | Q(owner__phone__icontains=query)
                | Q(owner__whatsapp__icontains=query),
                is_active=True,
            )
            .select_related('owner', 'owner__branch')
            .only(
                'id', 'name', 'species', 'breed', 'photo',
                'owner__first_name', 'owner__last_name', 'owner__phone',
                'owner__branch__name',
            )[:15]
        )

        return Response({'results': [p.to_search_dict() for p in patients]})


class MediaAuthView(APIView):
    """
    Nginx internal auth_request endpoint.
    Returns 200 for authenticated users, 401 otherwise.
    Protects /media/ files from unauthenticated access.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(status=200)


# ── Dashboard ──────────────────────────────────────────────────────────────

class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'dashboard/index.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.appointments.models import Appointment
        from apps.analytics.reports import dashboard_stats

        today = timezone.now().date()
        try:
            branch = self.request.user.staff_profile.branch
        except Exception:
            branch = None

        if branch:
            ctx['appointments_today'] = (
                Appointment.objects
                .filter(branch=branch, scheduled_at__date=today)
                .select_related('patient', 'patient__owner', 'veterinarian')
                .order_by('scheduled_at')
            )
            ctx['stats'] = dashboard_stats(branch.pk)
        return ctx


# ── Patient views ──────────────────────────────────────────────────────────

@login_required
def patient_list(request):
    from apps.patients.models import Patient
    patients = Patient.objects.filter(is_active=True).select_related(
        'owner', 'owner__branch'
    )
    try:
        branch = request.user.staff_profile.branch
        if branch:
            patients = patients.filter(owner__branch=branch)
    except Exception:
        pass

    search = request.GET.get('q', '').strip()
    if search:
        patients = patients.filter(
            Q(name__icontains=search)
            | Q(owner__first_name__icontains=search)
            | Q(owner__last_name__icontains=search)
            | Q(owner__phone__icontains=search)
        )

    patients = patients.order_by('name')
    template = 'patients/list.html'
    if request.headers.get('HX-Request'):
        template = 'patients/_table.html'
    return render(request, template, {'patients': patients, 'search': search})


@login_required
def patient_detail(request, pk: int):
    patient = get_object_or_404(
        Patient.objects.select_related('owner', 'owner__branch')
        .prefetch_related('visits', 'vaccinations', 'weight_history'),
        pk=pk,
    )
    from apps.patients.models import Patient
    return render(request, 'patients/detail.html', {'patient': patient})


# ── Appointment queue views ────────────────────────────────────────────────

@login_required
def appointment_card(request, pk: int):
    """Returns just the appointment card HTML for HTMX partial swap."""
    from apps.appointments.models import Appointment
    appt = get_object_or_404(
        Appointment.objects.select_related('patient', 'patient__owner', 'veterinarian'),
        pk=pk,
    )
    return render(request, 'appointments/_card.html', {'appointment': appt})


@login_required
def appointment_status_update(request, pk: int):
    """HTMX: one-tap status advance from the queue card."""
    from apps.appointments.models import Appointment
    from apps.core.utils import notify_branch_ws

    if request.method != 'POST':
        return HttpResponse(status=405)

    appt = get_object_or_404(Appointment, pk=pk)
    if appt.status not in appt.TERMINAL_STATUSES:
        old = appt.status
        appt.status = appt.advance_status()
        appt.save(update_fields=['status', 'updated_at'])
        notify_branch_ws(
            branch_id=appt.branch_id,
            event_type='appointment.status_changed',
            data={
                'appointment_id': appt.pk,
                'new_status': appt.status,
                'patient_name': appt.patient.name,
                'updated_by': request.user.get_full_name(),
                'timestamp': timezone.now().isoformat(),
            },
        )

    return render(request, 'appointments/_card.html', {'appointment': appt})


# ── EMR Views ──────────────────────────────────────────────────────────────

@login_required
def consultation_detail(request, pk: int):
    from apps.emr.models import Consultation
    consultation = get_object_or_404(
        Consultation.objects.select_related('patient', 'attending_vet', 'branch')
        .prefetch_related('prescriptions__inventory_item', 'attachments'),
        pk=pk,
    )
    return render(request, 'emr/consultation.html', {'consultation': consultation})


# ── Inventory views ────────────────────────────────────────────────────────

@login_required
def inventory_list(request):
    from apps.inventory.models import InventoryItem
    from django.db.models import F

    try:
        branch = request.user.staff_profile.branch
    except Exception:
        branch = None

    items = InventoryItem.objects.filter(is_active=True)
    if branch:
        items = items.filter(branch=branch)

    tab = request.GET.get('tab', 'all')
    if tab == 'alerts':
        items = items.filter(stock_quantity__lte=F('reorder_level'))
    elif tab == 'forecast':
        items = items.filter(
            category__in=['MED', 'VACCINE', 'SUPPLY'],
            avg_daily_consumption__isnull=False,
        ).order_by('predicted_stockout_date')

    return render(request, 'inventory/list.html', {'items': items, 'tab': tab})


@login_required
def inventory_forecast_fragment(request):
    """HTMX partial: forecast table loaded lazily."""
    from apps.analytics.views import InventoryForecastView
    view = InventoryForecastView()
    view.request = request
    response = view.get(request)
    return render(request, 'inventory/_forecast_table.html', {'items': response.data})


# ── Revenue widget (HTMX partial) ──────────────────────────────────────────

@login_required
def revenue_widget(request):
    from apps.analytics.reports import dashboard_stats
    try:
        branch_id = request.user.staff_profile.branch_id
    except Exception:
        return HttpResponse('')
    stats = dashboard_stats(branch_id)
    return render(request, 'dashboard/_revenue_widget.html', {'stats': stats})
