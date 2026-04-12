from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import Patient, WeightRecord, VaccinationRecord
from .serializers import (
    PatientSerializer, PatientListSerializer,
    WeightRecordSerializer, VaccinationRecordSerializer,
)


class PatientViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['species', 'gender', 'is_active', 'is_deceased', 'owner']
    search_fields = ['name', 'microchip_number', 'owner__first_name',
                     'owner__last_name', 'owner__phone']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    def get_serializer_class(self):
        if self.action == 'list':
            return PatientListSerializer
        return PatientSerializer

    def get_queryset(self):
        return Patient.objects.select_related(
            'owner', 'owner__branch'
        ).prefetch_related('weight_history', 'vaccinations')


class WeightRecordViewSet(viewsets.ModelViewSet):
    serializer_class = WeightRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['patient']

    def get_queryset(self):
        return WeightRecord.objects.select_related('patient', 'recorded_by')


class VaccinationViewSet(viewsets.ModelViewSet):
    serializer_class = VaccinationRecordSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['patient', 'reminder_sent']

    def get_queryset(self):
        return VaccinationRecord.objects.select_related(
            'patient', 'administered_by', 'inventory_item'
        )
