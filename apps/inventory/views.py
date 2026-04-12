from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from .models import InventoryItem, StockTransaction
from .serializers import (
    InventoryItemSerializer, InventoryItemListSerializer, StockTransactionSerializer
)


class InventoryItemViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['branch', 'category', 'is_active', 'is_controlled_drug',
                        'requires_prescription']
    search_fields = ['name', 'generic_name', 'sku', 'barcode']
    ordering_fields = ['name', 'stock_quantity', 'selling_price', 'expiry_date']
    ordering = ['category', 'name']

    def get_serializer_class(self):
        if self.action == 'list' and self.request.query_params.get('compact'):
            return InventoryItemListSerializer
        return InventoryItemSerializer

    def get_queryset(self):
        qs = InventoryItem.objects.all()
        try:
            branch = self.request.user.staff_profile.branch
            if branch:
                qs = qs.filter(branch=branch)
        except Exception:
            pass

        low_stock = self.request.query_params.get('low_stock')
        if low_stock:
            from django.db.models import F
            qs = qs.filter(stock_quantity__lte=F('reorder_level'), is_active=True)

        expiring_days = self.request.query_params.get('expiring_days')
        if expiring_days:
            from django.utils import timezone
            import datetime
            cutoff = timezone.now().date() + datetime.timedelta(days=int(expiring_days))
            qs = qs.filter(expiry_date__lte=cutoff, is_active=True)

        return qs


class StockTransactionViewSet(viewsets.ModelViewSet):
    serializer_class = StockTransactionSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['item', 'transaction_type']
    http_method_names = ['get', 'post', 'head', 'options']  # No PUT/PATCH/DELETE on ledger

    def get_queryset(self):
        return StockTransaction.objects.select_related('item', 'performed_by')
