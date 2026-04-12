"""
API integration tests — DRF endpoints.
Uses APIClient with forced authentication (no token overhead).
"""
import pytest
from decimal import Decimal
from django.urls import reverse


class TestPatientAPI:
    def test_list_patients_authenticated(self, api_client, patient):
        r = api_client.get('/api/v1/patients/')
        assert r.status_code == 200
        assert r.data['count'] >= 1

    def test_list_patients_unauthenticated(self, client):
        r = client.get('/api/v1/patients/')
        assert r.status_code in (401, 403)

    def test_retrieve_patient(self, api_client, patient):
        r = api_client.get(f'/api/v1/patients/{patient.pk}/')
        assert r.status_code == 200
        assert r.data['name'] == patient.name
        assert 'species_emoji' in r.data

    def test_create_patient(self, api_client, client_obj):
        r = api_client.post('/api/v1/patients/', {
            'owner': client_obj.pk,
            'name': 'NewDog',
            'species': 'DOG',
            'breed': 'Poodle',
            'gender': 'F',
            'current_weight_kg': '8.0',
        })
        assert r.status_code == 201
        assert r.data['name'] == 'NewDog'

    def test_search_patient_by_name(self, api_client, patient):
        r = api_client.get('/api/v1/search/?q=TestDog')
        assert r.status_code == 200
        results = r.data['results']
        assert any(p['name'] == 'TestDog' for p in results)

    def test_search_requires_min_2_chars(self, api_client):
        r = api_client.get('/api/v1/search/?q=T')
        assert r.status_code == 200
        assert r.data['results'] == []


class TestConsultationAPI:
    def test_create_consultation(self, api_client, patient, vet_user, branch):
        r = api_client.post('/api/v1/consultations/', {
            'patient': patient.pk,
            'branch': branch.pk,
            'subjective': 'Dog is limping',
            'objective': 'Swelling noted on left forelimb',
            'assessment': 'Suspected sprain',
            'plan': 'Rest + NSAID',
        })
        assert r.status_code == 201
        assert r.data['status'] == 'OPEN'

    def test_finalize_consultation(self, api_client, consultation, vet_user):
        r = api_client.post(f'/api/v1/consultations/{consultation.pk}/finalize/')
        assert r.status_code == 200
        assert r.data['status'] == 'CLOSED'

    def test_cannot_finalize_closed_consultation(self, api_client, consultation, vet_user):
        consultation.finalize(vet_user)
        r = api_client.post(f'/api/v1/consultations/{consultation.pk}/finalize/')
        assert r.status_code == 400


class TestInventoryAPI:
    def test_list_inventory(self, api_client, inventory_item):
        r = api_client.get('/api/v1/inventory/')
        assert r.status_code == 200
        assert r.data['count'] >= 1

    def test_low_stock_filter(self, api_client, inventory_item):
        inventory_item.stock_quantity = inventory_item.reorder_level
        inventory_item.save()
        r = api_client.get('/api/v1/inventory/?low_stock=1')
        assert r.status_code == 200
        assert r.data['count'] >= 1


class TestAppointmentAPI:
    def test_advance_appointment_status(self, db, api_client, patient, vet_user, branch):
        from apps.appointments.models import Appointment
        from django.utils import timezone
        appt = Appointment.objects.create(
            patient=patient, veterinarian=vet_user, branch=branch,
            scheduled_at=timezone.now(),
            appointment_type='CONSULT', status='BOOKED',
            created_by=vet_user,
        )
        r = api_client.post(f'/api/v1/appointments/{appt.pk}/advance/')
        assert r.status_code == 200
        assert r.data['status'] == 'CHECKED_IN'

    def test_cancel_appointment(self, db, api_client, patient, vet_user, branch):
        from apps.appointments.models import Appointment
        from django.utils import timezone
        appt = Appointment.objects.create(
            patient=patient, veterinarian=vet_user, branch=branch,
            scheduled_at=timezone.now(),
            appointment_type='CONSULT', status='BOOKED',
            created_by=vet_user,
        )
        r = api_client.post(f'/api/v1/appointments/{appt.pk}/cancel/')
        assert r.status_code == 200
        appt.refresh_from_db()
        assert appt.status == 'CANCELLED'


class TestBillingAPI:
    def test_pay_invoice(self, db, api_client, consultation, inventory_item, vet_user):
        from apps.billing.models import Invoice, InvoiceLineItem
        consultation.finalize(vet_user)
        invoice = Invoice.objects.get(consultation=consultation)

        r = api_client.post(f'/api/v1/invoices/{invoice.pk}/pay/', {
            'payment_method': 'CASH',
            'paid_amount': str(invoice.total_amount),
        })
        assert r.status_code == 200
        assert r.data['status'] == 'PAID'

    def test_void_invoice(self, db, api_client, consultation, vet_user):
        from apps.billing.models import Invoice
        consultation.finalize(vet_user)
        invoice = Invoice.objects.get(consultation=consultation)

        r = api_client.post(f'/api/v1/invoices/{invoice.pk}/void/')
        assert r.status_code == 200
        invoice.refresh_from_db()
        assert invoice.status == 'VOID'
