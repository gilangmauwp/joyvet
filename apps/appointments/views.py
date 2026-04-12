"""
Appointment API views — CRUD + one-tap status progression.
"""
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from .models import Appointment
from .serializers import AppointmentSerializer
from apps.core.utils import write_audit_log, notify_branch_ws


class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Appointment.objects.select_related(
            'patient', 'patient__owner', 'veterinarian', 'branch'
        )
        # Filter to user's branch by default
        try:
            branch = self.request.user.staff_profile.branch
            if branch:
                qs = qs.filter(branch=branch)
        except Exception:
            pass

        # Date filter
        date_str = self.request.query_params.get('date')
        if date_str:
            qs = qs.filter(scheduled_at__date=date_str)

        # Today's queue (default for dashboard)
        if self.request.query_params.get('today'):
            today = timezone.now().date()
            qs = qs.filter(scheduled_at__date=today)

        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)

        vet_id = self.request.query_params.get('vet')
        if vet_id:
            qs = qs.filter(veterinarian_id=vet_id)

        return qs.order_by('scheduled_at')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='advance')
    def advance_status(self, request, pk=None):
        """One-tap status advancement for the check-in dashboard."""
        appt = self.get_object()
        if appt.status in appt.TERMINAL_STATUSES:
            return Response(
                {'error': f'Cannot advance from {appt.status}'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        old_status = appt.status
        new_status = appt.advance_status()
        appt.status = new_status
        appt.save(update_fields=['status', 'updated_at'])

        # Real-time notification to all branch devices
        notify_branch_ws(
            branch_id=appt.branch_id,
            event_type='appointment.status_changed',
            data={
                'appointment_id': appt.pk,
                'new_status': new_status,
                'patient_name': appt.patient.name,
                'updated_by': request.user.get_full_name(),
                'timestamp': timezone.now().isoformat(),
            },
        )

        write_audit_log(
            user=request.user,
            action='UPDATE',
            model_name='Appointment',
            object_id=str(appt.pk),
            changes={'status': [old_status, new_status]},
        )

        return Response(AppointmentSerializer(appt).data)

    @action(detail=True, methods=['post'], url_path='cancel')
    def cancel(self, request, pk=None):
        appt = self.get_object()
        if appt.status in appt.TERMINAL_STATUSES:
            return Response({'error': 'Already in terminal status.'}, status=400)
        old_status = appt.status
        appt.status = 'CANCELLED'
        appt.save(update_fields=['status', 'updated_at'])
        write_audit_log(
            user=request.user, action='UPDATE', model_name='Appointment',
            object_id=str(appt.pk), changes={'status': [old_status, 'CANCELLED']},
        )
        return Response({'status': 'cancelled'})
