"""
Billing signals.

Key design: stock is deducted ONLY when an invoice transitions to PAID.
This prevents ghost stock deductions when invoices are voided or edited.

Pattern:
  pre_save  → cache old status on instance
  post_save → compare old vs new; deduct if PAID transition
"""
from django.db import transaction
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from apps.core.utils import write_audit_log, notify_branch_ws


@receiver(pre_save, sender='billing.Invoice')
def cache_old_invoice_status(sender, instance, **kwargs) -> None:
    """Store the pre-save status so post_save can detect transitions."""
    if instance.pk:
        try:
            instance._old_status = sender.objects.get(pk=instance.pk).status
        except sender.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None


@receiver(post_save, sender='billing.Invoice')
def on_invoice_status_changed(sender, instance, created, **kwargs) -> None:
    """
    Fires on every Invoice save.
    Deduct stock only on the PENDING → PAID transition.
    Void reversal is handled separately.
    """
    old_status = getattr(instance, '_old_status', None)
    new_status = instance.status

    # ── PAID transition ────────────────────────────────────────────────
    if new_status == 'PAID' and old_status != 'PAID':
        _deduct_stock_for_invoice(instance)
        _notify_invoice_paid(instance)
        write_audit_log(
            user=instance.created_by,
            action='UPDATE',
            model_name='Invoice',
            object_id=str(instance.pk),
            object_repr=instance.invoice_number,
            changes={'status': [old_status, 'PAID'],
                     'paid_amount': [str(old_status), str(instance.paid_amount)]},
        )

    # ── VOID transition ────────────────────────────────────────────────
    if new_status == 'VOID' and old_status == 'PAID':
        _restore_stock_for_invoice(instance)
        write_audit_log(
            user=instance.created_by,
            action='VOID',
            model_name='Invoice',
            object_id=str(instance.pk),
            object_repr=instance.invoice_number,
            changes={'status': ['PAID', 'VOID']},
        )


def _deduct_stock_for_invoice(invoice) -> None:
    """Deduct stock for every line item and create StockTransaction records."""
    from apps.inventory.models import InventoryItem, StockTransaction
    from apps.inventory.tasks import send_low_stock_alert

    with transaction.atomic():
        for line in invoice.items.select_related('inventory_item'):
            item = line.inventory_item
            if item.category == 'SERVICE':
                continue  # Non-stock services don't affect inventory

            InventoryItem.objects.filter(pk=item.pk).update(
                stock_quantity=models_F('stock_quantity') - line.quantity
            )
            # Re-fetch to get accurate balance_after
            item.refresh_from_db(fields=['stock_quantity'])

            StockTransaction.objects.create(
                item=item,
                transaction_type='SALE',
                quantity=-line.quantity,
                balance_after=item.stock_quantity,
                reference_id=invoice.invoice_number,
                performed_by=invoice.created_by,
            )

            if item.is_low_stock:
                send_low_stock_alert.delay(item.pk)


def _restore_stock_for_invoice(invoice) -> None:
    """Reverse stock deductions when a PAID invoice is voided."""
    from apps.inventory.models import InventoryItem, StockTransaction

    with transaction.atomic():
        for line in invoice.items.select_related('inventory_item'):
            item = line.inventory_item
            if item.category == 'SERVICE':
                continue

            InventoryItem.objects.filter(pk=item.pk).update(
                stock_quantity=models_F('stock_quantity') + line.quantity
            )
            item.refresh_from_db(fields=['stock_quantity'])

            StockTransaction.objects.create(
                item=item,
                transaction_type='RETURN',
                quantity=line.quantity,
                balance_after=item.stock_quantity,
                reference_id=f"VOID-{invoice.invoice_number}",
                performed_by=invoice.created_by,
                notes=f"Stock restored: invoice {invoice.invoice_number} voided",
            )


def _notify_invoice_paid(invoice) -> None:
    """Push real-time payment notification to all branch devices."""
    try:
        notify_branch_ws(
            branch_id=invoice.branch_id,
            event_type='invoice.paid',
            data={
                'invoice_number': invoice.invoice_number,
                'amount': str(invoice.total_amount),
                'patient_name': invoice.consultation.patient.name,
                'payment_method': invoice.get_payment_method_display(),
            },
        )
    except Exception:
        pass  # WS failure must never break a payment


def models_F(field: str):
    """Lazy import of F to avoid circular import at module load."""
    from django.db.models import F
    return F(field)
