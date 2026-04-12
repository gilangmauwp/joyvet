from rest_framework import serializers
from .models import InventoryItem, StockTransaction


class InventoryItemSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    is_low_stock = serializers.ReadOnlyField()
    is_out_of_stock = serializers.ReadOnlyField()
    days_until_expiry = serializers.ReadOnlyField()
    margin_percent = serializers.ReadOnlyField()

    class Meta:
        model = InventoryItem
        fields = [
            'id', 'branch', 'name', 'generic_name', 'category', 'category_display',
            'sku', 'barcode', 'unit',
            'cost_price', 'selling_price', 'tax_rate', 'margin_percent',
            'stock_quantity', 'reorder_level', 'max_stock',
            'expiry_date', 'batch_number', 'days_until_expiry',
            'is_controlled_drug', 'requires_prescription', 'is_active',
            'avg_daily_consumption', 'predicted_stockout_date', 'restock_recommendation',
            'is_low_stock', 'is_out_of_stock',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'avg_daily_consumption', 'predicted_stockout_date',
            'restock_recommendation', 'created_at', 'updated_at',
        ]


class InventoryItemListSerializer(serializers.ModelSerializer):
    """Compact for POS item picker."""
    is_low_stock = serializers.ReadOnlyField()

    class Meta:
        model = InventoryItem
        fields = ['id', 'name', 'sku', 'category', 'unit',
                  'selling_price', 'stock_quantity', 'is_low_stock', 'is_active']


class StockTransactionSerializer(serializers.ModelSerializer):
    item_name = serializers.SerializerMethodField()
    type_display = serializers.CharField(source='get_transaction_type_display', read_only=True)

    class Meta:
        model = StockTransaction
        fields = [
            'id', 'item', 'item_name', 'transaction_type', 'type_display',
            'quantity', 'balance_after', 'reference_id',
            'performed_by', 'notes', 'created_at',
        ]
        read_only_fields = ['id', 'balance_after', 'created_at']

    def get_item_name(self, obj) -> str:
        return obj.item.name

    def create(self, validated_data):
        item = validated_data['item']
        qty = validated_data['quantity']
        item.stock_quantity += qty
        item.save(update_fields=['stock_quantity'])
        validated_data['balance_after'] = item.stock_quantity
        validated_data['performed_by'] = self.context['request'].user
        return super().create(validated_data)
