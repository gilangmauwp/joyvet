"""
Billing / POS API views.
"""
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from api.permissions import CanViewFinancials
from .models import Invoice, InvoiceLineItem
from .serializers import InvoiceSerializer, InvoiceLineItemSerializer, PayInvoiceSerializer
from apps.core.utils import write_audit_log


class InvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'revenue_summary'):
            return [IsAuthenticated(), CanViewFinancials()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = Invoice.objects.select_related(
            'consultation__patient', 'consultation__patient__owner',
            'branch', 'created_by',
        ).prefetch_related('items__inventory_item')

        # Branch scoping
        try:
            branch = self.request.user.staff_profile.branch
            if branch:
                qs = qs.filter(branch=branch)
        except Exception:
            pass

        status_f = self.request.query_params.get('status')
        if status_f:
            qs = qs.filter(status=status_f)

        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        if date_from and date_to:
            qs = qs.filter(created_at__date__range=[date_from, date_to])

        return qs.order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'], url_path='pay')
    def pay(self, request, pk=None):
        """Process payment — transitions invoice to PAID or PARTIAL."""
        invoice = self.get_object()
        if invoice.status in ('PAID', 'VOID'):
            return Response(
                {'error': f'Invoice is already {invoice.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = PayInvoiceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        invoice.paid_amount += data['paid_amount']
        invoice.payment_method = data['payment_method']
        invoice.payment_reference = data.get('payment_reference', '')

        if invoice.paid_amount >= invoice.total_amount:
            invoice.status = 'PAID'
            invoice.paid_at = timezone.now()
        else:
            invoice.status = 'PARTIAL'

        invoice.save(update_fields=[
            'paid_amount', 'payment_method', 'payment_reference',
            'status', 'paid_at', 'updated_at',
        ])

        return Response(InvoiceSerializer(invoice).data)

    @action(detail=True, methods=['post'], url_path='void')
    def void(self, request, pk=None):
        """Void an invoice — reverses stock if it was PAID."""
        invoice = self.get_object()
        if invoice.status == 'VOID':
            return Response({'error': 'Already voided.'}, status=400)

        old_status = invoice.status
        invoice.status = 'VOID'
        invoice.save(update_fields=['status', 'updated_at'])

        write_audit_log(
            user=request.user, action='VOID', model_name='Invoice',
            object_id=str(invoice.pk), object_repr=invoice.invoice_number,
            changes={'status': [old_status, 'VOID'],
                     'reason': request.data.get('reason', '')},
        )
        return Response({'status': 'voided'})

    @action(detail=True, methods=['post'], url_path='add-line')
    def add_line_item(self, request, pk=None):
        """Add a line item to a DRAFT/PENDING invoice."""
        invoice = self.get_object()
        if invoice.status not in ('DRAFT', 'PENDING'):
            return Response({'error': 'Can only edit DRAFT or PENDING invoices.'}, status=400)

        s = InvoiceLineItemSerializer(data={**request.data, 'invoice': invoice.pk})
        s.is_valid(raise_exception=True)
        s.save()
        invoice.recalculate_totals()
        return Response(InvoiceSerializer(invoice).data, status=status.HTTP_201_CREATED)
