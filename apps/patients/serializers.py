from rest_framework import serializers
from .models import Patient, WeightRecord, VaccinationRecord


class WeightRecordSerializer(serializers.ModelSerializer):
    recorded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = WeightRecord
        fields = ['id', 'weight_kg', 'recorded_at', 'recorded_by',
                  'recorded_by_name', 'notes']
        read_only_fields = ['id', 'recorded_at']

    def get_recorded_by_name(self, obj) -> str:
        return obj.recorded_by.get_full_name() if obj.recorded_by else ''

    def create(self, validated_data):
        validated_data['recorded_by'] = self.context['request'].user
        return super().create(validated_data)


class VaccinationRecordSerializer(serializers.ModelSerializer):
    is_overdue = serializers.ReadOnlyField()
    days_until_due = serializers.ReadOnlyField()
    administered_by_name = serializers.SerializerMethodField()

    class Meta:
        model = VaccinationRecord
        fields = [
            'id', 'vaccine_name', 'batch_number', 'administered_date',
            'next_due_date', 'administered_by', 'administered_by_name',
            'inventory_item', 'reminder_sent', 'notes',
            'is_overdue', 'days_until_due', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def get_administered_by_name(self, obj) -> str:
        return obj.administered_by.get_full_name() if obj.administered_by else ''


class PatientSerializer(serializers.ModelSerializer):
    species_display = serializers.CharField(source='get_species_display', read_only=True)
    gender_display = serializers.CharField(source='get_gender_display', read_only=True)
    species_emoji = serializers.ReadOnlyField()
    age_display = serializers.ReadOnlyField()
    owner_name = serializers.SerializerMethodField()
    owner_phone = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = [
            'id', 'owner', 'owner_name', 'owner_phone',
            'name', 'species', 'species_display', 'species_emoji',
            'breed', 'gender', 'gender_display',
            'birth_date', 'age_display', 'microchip_number',
            'current_weight_kg', 'photo', 'qr_code',
            'known_allergies', 'insurance_provider', 'insurance_number',
            'is_deceased', 'is_active', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'qr_code', 'created_at', 'updated_at']

    def get_owner_name(self, obj) -> str:
        return obj.owner.full_name

    def get_owner_phone(self, obj) -> str:
        return obj.owner.phone


class PatientListSerializer(serializers.ModelSerializer):
    """Lightweight for list + global search."""
    species_emoji = serializers.ReadOnlyField()
    owner_name = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = ['id', 'name', 'species', 'species_emoji', 'breed',
                  'owner', 'owner_name', 'photo', 'is_active']

    def get_owner_name(self, obj) -> str:
        return obj.owner.full_name
