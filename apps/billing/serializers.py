from decimal import Decimal
from rest_framework import serializers
from .models import Invoice, InvoiceLineItem


class InvoiceLineItemSerializer(serializers.ModelSerializer):
    item_name = serializers.SerializerMethodField()

    class Meta:
        model = InvoiceLineItem
        fields = [
            'id', 'inventory_item', 'item_name', 'description',
            'quantity', 'unit_price', 'discount_percent', 'subtotal',
        ]
        read_only_fields = ['id', 'subtotal']

    def get_item_name(self, obj) -> str:
        return obj.inventory_item.name


class InvoiceSerializer(serializers.ModelSerializer):
    items = InvoiceLineItemSerializer(many=True, read_only=True)
    patient_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    payment_method_display = serializers.CharField(
        source='get_payment_method_display', read_only=True
    )
    balance_due = serializers.ReadOnlyField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'consultation', 'branch', 'invoice_number',
            'status', 'status_display',
            'subtotal', 'discount_amount', 'tax_amount', 'total_amount',
            'paid_amount', 'balance_due',
            'payment_method', 'payment_method_display', 'payment_reference',
            'notes', 'created_by', 'created_at', 'paid_at', 'updated_at',
            'patient_name', 'items',
        ]
        read_only_fields = [
            'id', 'invoice_number', 'subtotal', 'tax_amount', 'total_amount',
            'created_at', 'updated_at', 'paid_at',
        ]

    def get_patient_name(self, obj) -> str:
        return obj.consultation.patient.name


class PayInvoiceSerializer(serializers.Serializer):
    """Used for the POST /invoices/{id}/pay/ endpoint."""
    payment_method = serializers.ChoiceField(choices=Invoice.PAYMENT_METHODS)
    paid_amount = serializers.DecimalField(max_digits=14, decimal_places=0)
    payment_reference = serializers.CharField(max_length=100, allow_blank=True, default='')

    def validate_paid_amount(self, value):
        if value <= Decimal('0'):
            raise serializers.ValidationError("Payment amount must be positive.")
        return value
