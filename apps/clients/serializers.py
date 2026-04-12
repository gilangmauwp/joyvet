from rest_framework import serializers
from .models import Client


class ClientSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    contact_number = serializers.ReadOnlyField()
    pet_count = serializers.SerializerMethodField()

    class Meta:
        model = Client
        fields = [
            'id', 'branch', 'first_name', 'last_name', 'full_name',
            'phone', 'whatsapp', 'email', 'address', 'id_number',
            'preferred_contact', 'notes', 'is_active',
            'pet_count', 'contact_number', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_pet_count(self, obj) -> int:
        return obj.pets.filter(is_active=True).count()


class ClientListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views and search results."""
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = Client
        fields = ['id', 'full_name', 'phone', 'whatsapp', 'branch', 'created_at']
