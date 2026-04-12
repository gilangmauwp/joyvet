from rest_framework import serializers
from .models import Consultation, MedicalAttachment, Prescription


class PrescriptionSerializer(serializers.ModelSerializer):
    item_name = serializers.SerializerMethodField()

    class Meta:
        model = Prescription
        fields = [
            'id', 'consultation', 'inventory_item', 'item_name',
            'dosage', 'frequency', 'duration_days', 'quantity',
            'notes', 'is_controlled_drug', 'witnessed_by', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_item_name(self, obj) -> str:
        return obj.inventory_item.name

    def validate(self, data):
        if data.get('is_controlled_drug') and not data.get('witnessed_by'):
            raise serializers.ValidationError(
                {'witnessed_by': 'Controlled drugs require a witness.'}
            )
        return data


class MedicalAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = MedicalAttachment
        fields = [
            'id', 'consultation', 'file', 'file_type', 'description',
            'uploaded_by', 'uploaded_by_name', 'uploaded_at',
            'source_device', 'is_from_camera',
        ]
        read_only_fields = ['id', 'uploaded_at', 'uploaded_by']

    def get_uploaded_by_name(self, obj) -> str:
        return obj.uploaded_by.get_full_name() if obj.uploaded_by else ''


class ConsultationSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    vet_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    prescriptions = PrescriptionSerializer(many=True, read_only=True)
    attachments = MedicalAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Consultation
        fields = [
            'id', 'patient', 'patient_name', 'attending_vet', 'vet_name',
            'branch', 'visit_date', 'appointment',
            'subjective', 'objective', 'assessment', 'plan',
            'temperature_celsius', 'heart_rate_bpm', 'respiratory_rate',
            'weight_kg', 'capillary_refill_time', 'mucous_membrane_color',
            'status', 'status_display', 'version',
            'finalized_by', 'finalized_at',
            'follow_up_date', 'internal_notes',
            'prescriptions', 'attachments',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'status', 'version', 'finalized_by', 'finalized_at',
            'created_at', 'updated_at',
        ]

    def get_patient_name(self, obj) -> str:
        return obj.patient.name

    def get_vet_name(self, obj) -> str:
        return obj.attending_vet.get_full_name()


class ConsultationListSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    vet_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Consultation
        fields = ['id', 'patient', 'patient_name', 'attending_vet', 'vet_name',
                  'visit_date', 'status', 'status_display', 'branch']

    def get_patient_name(self, obj) -> str:
        return obj.patient.name

    def get_vet_name(self, obj) -> str:
        return obj.attending_vet.get_full_name()
