"""
Model unit tests — business logic, constraints, property methods.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.utils import timezone


class TestPatientModel:
    def test_species_emoji(self, patient):
        assert patient.species_emoji == '🐶'

    def test_age_display(self, patient):
        assert 'y' in patient.age_display or 'months' in patient.age_display

    def test_to_search_dict_keys(self, patient):
        d = patient.to_search_dict()
        assert 'id' in d
        assert 'name' in d
        assert 'species_emoji' in d
        assert 'owner_name' in d


class TestClientModel:
    def test_full_name(self, client_obj):
        assert client_obj.full_name == 'Test Owner'

    def test_contact_number_prefers_whatsapp(self, client_obj):
        client_obj.whatsapp = '08200000002'
        assert client_obj.contact_number == '08200000002'

    def test_contact_number_falls_back_to_phone(self, client_obj):
        client_obj.whatsapp = ''
        assert client_obj.contact_number == client_obj.phone


class TestInventoryItem:
    def test_is_low_stock_when_at_reorder_level(self, inventory_item):
        inventory_item.stock_quantity = inventory_item.reorder_level
        assert inventory_item.is_low_stock is True

    def test_is_not_low_stock_when_above_reorder(self, inventory_item):
        inventory_item.stock_quantity = inventory_item.reorder_level + Decimal('1')
        assert inventory_item.is_low_stock is False

    def test_is_out_of_stock(self, inventory_item):
        inventory_item.stock_quantity = Decimal('0')
        assert inventory_item.is_out_of_stock is True

    def test_days_until_expiry(self, inventory_item):
        inventory_item.expiry_date = date.today() + timedelta(days=10)
        assert inventory_item.days_until_expiry == 10

    def test_margin_percent(self, inventory_item):
        # selling=15000, cost=5000 → margin=200%
        assert inventory_item.margin_percent == Decimal('200.0')


class TestConsultation:
    def test_finalize_sets_status_to_closed(self, consultation, vet_user):
        consultation.finalize(vet_user)
        assert consultation.status == 'CLOSED'
        assert consultation.finalized_by == vet_user
        assert consultation.finalized_at is not None

    def test_finalize_twice_raises_error(self, consultation, vet_user):
        consultation.finalize(vet_user)
        with pytest.raises(ValueError, match='already finalized'):
            consultation.finalize(vet_user)

    def test_version_increments_on_finalize(self, consultation, vet_user):
        old_version = consultation.version
        consultation.finalize(vet_user)
        assert consultation.version == old_version + 1


class TestAppointment:
    def test_advance_status_from_booked(self, patient, vet_user, branch):
        from apps.appointments.models import Appointment
        appt = Appointment(status='BOOKED')
        assert appt.advance_status() == 'CHECKED_IN'

    def test_advance_status_from_checked_in(self, patient, vet_user, branch):
        from apps.appointments.models import Appointment
        appt = Appointment(status='CHECKED_IN')
        assert appt.advance_status() == 'IN_PROGRESS'

    def test_advance_status_from_in_progress(self, patient, vet_user, branch):
        from apps.appointments.models import Appointment
        appt = Appointment(status='IN_PROGRESS')
        assert appt.advance_status() == 'COMPLETED'


class TestBillingInvoiceLineItem:
    def test_subtotal_calculated_on_save(self, db, consultation, inventory_item):
        from apps.billing.models import Invoice, InvoiceLineItem
        invoice = Invoice.objects.create(
            consultation=consultation,
            branch=consultation.branch,
            status='DRAFT',
            created_by=consultation.attending_vet,
        )
        line = InvoiceLineItem.objects.create(
            invoice=invoice,
            inventory_item=inventory_item,
            quantity=Decimal('3'),
            unit_price=Decimal('15000'),
            discount_percent=Decimal('0'),
        )
        assert line.subtotal == Decimal('45000')

    def test_subtotal_with_discount(self, db, consultation, inventory_item):
        from apps.billing.models import Invoice, InvoiceLineItem
        invoice = Invoice.objects.create(
            consultation=consultation,
            branch=consultation.branch,
            status='DRAFT',
            created_by=consultation.attending_vet,
        )
        line = InvoiceLineItem.objects.create(
            invoice=invoice,
            inventory_item=inventory_item,
            quantity=Decimal('2'),
            unit_price=Decimal('10000'),
            discount_percent=Decimal('10'),  # 10% off
        )
        # 2 × 10000 = 20000, less 10% = 18000
        assert line.subtotal == Decimal('18000')
