from rest_framework import serializers
from .models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    patient_species_emoji = serializers.SerializerMethodField()
    vet_name = serializers.SerializerMethodField()
    owner_phone = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display = serializers.CharField(source='get_appointment_type_display', read_only=True)
    next_status = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'patient_name', 'patient_species_emoji',
            'veterinarian', 'vet_name', 'owner_phone',
            'branch', 'scheduled_at', 'duration_minutes',
            'appointment_type', 'type_display',
            'status', 'status_display', 'next_status',
            'reason', 'internal_notes',
            'reminder_24h_sent', 'reminder_1h_sent',
            'created_by', 'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'reminder_24h_sent', 'reminder_1h_sent',
            'created_at', 'updated_at',
        ]

    def get_patient_name(self, obj) -> str:
        return obj.patient.name

    def get_patient_species_emoji(self, obj) -> str:
        return obj.patient.species_emoji

    def get_vet_name(self, obj) -> str:
        return obj.veterinarian.get_full_name()

    def get_owner_phone(self, obj) -> str:
        return obj.patient.owner.phone

    def get_next_status(self, obj) -> str:
        return obj.advance_status()
