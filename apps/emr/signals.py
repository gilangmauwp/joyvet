"""
EMR signals — auto-create Invoice when a Consultation is finalized.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender='emr.Consultation')
def create_invoice_on_finalize(sender, instance, created, **kwargs) -> None:
    """
    When a consultation transitions to CLOSED (finalized),
    auto-create a draft Invoice and populate line items from prescriptions.
    """
    if instance.status != 'CLOSED':
        return

    # Check if invoice already exists (idempotent)
    from apps.billing.models import Invoice, InvoiceLineItem
    if hasattr(instance, 'invoice'):
        return

    invoice = Invoice.objects.create(
        consultation=instance,
        branch=instance.branch,
        status='PENDING',
        created_by=instance.finalized_by or instance.attending_vet,
    )

    # Auto-add prescription items as line items
    for rx in instance.prescriptions.select_related('inventory_item').all():
        InvoiceLineItem.objects.create(
            invoice=invoice,
            inventory_item=rx.inventory_item,
            description=rx.inventory_item.name,
            quantity=rx.quantity,
            unit_price=rx.inventory_item.selling_price,
        )

    # Recalculate totals
    invoice.recalculate_totals()

    from apps.core.utils import write_audit_log
    write_audit_log(
        user=instance.finalized_by,
        action='FINALIZE',
        model_name='Consultation',
        object_id=str(instance.pk),
        object_repr=str(instance),
        changes={'invoice_created': invoice.invoice_number},
    )
