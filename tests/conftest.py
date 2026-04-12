"""
Pytest fixtures for JoyVet Care tests.
Uses pytest-django with a shared test database.
"""
import pytest
from decimal import Decimal
from datetime import date, timedelta
from django.contrib.auth.models import User
from django.utils import timezone


@pytest.fixture
def branch(db):
    from apps.core.models import Branch
    return Branch.objects.create(
        name='JoyVet Care Test',
        code='TST',
        address='Test Address',
        phone='0812345678',
    )


@pytest.fixture
def admin_user(db):
    user = User.objects.create_superuser(
        username='admin', password='testpass123',
        email='admin@test.com',
    )
    return user


@pytest.fixture
def vet_user(db, branch):
    from apps.core.models import StaffProfile
    user = User.objects.create_user(
        username='drtest', password='testpass123',
        first_name='Test', last_name='Vet',
    )
    StaffProfile.objects.create(
        user=user, branch=branch, role='VET',
        can_finalize_records=True, can_view_financials=True,
    )
    return user


@pytest.fixture
def receptionist_user(db, branch):
    from apps.core.models import StaffProfile
    user = User.objects.create_user(
        username='recept', password='testpass123',
        first_name='Test', last_name='Recept',
    )
    StaffProfile.objects.create(
        user=user, branch=branch, role='RECEPTIONIST',
        can_view_financials=True,
    )
    return user


@pytest.fixture
def client_obj(db, branch):
    from apps.clients.models import Client
    return Client.objects.create(
        branch=branch,
        first_name='Test',
        last_name='Owner',
        phone='08100000001',
        whatsapp='08100000001',
        preferred_contact='WA',
    )


@pytest.fixture
def patient(db, client_obj):
    from apps.patients.models import Patient
    return Patient.objects.create(
        owner=client_obj,
        name='TestDog',
        species='DOG',
        breed='Labrador',
        gender='M',
        current_weight_kg=Decimal('25.0'),
        birth_date=date(2020, 1, 1),
    )


@pytest.fixture
def inventory_item(db, branch):
    from apps.inventory.models import InventoryItem
    return InventoryItem.objects.create(
        branch=branch,
        name='Test Medicine',
        category='MED',
        sku='TST-MED-001',
        unit='tablet',
        cost_price=Decimal('5000'),
        selling_price=Decimal('15000'),
        stock_quantity=Decimal('100'),
        reorder_level=Decimal('10'),
        is_active=True,
    )


@pytest.fixture
def consultation(db, patient, vet_user, branch):
    from apps.emr.models import Consultation
    return Consultation.objects.create(
        patient=patient,
        attending_vet=vet_user,
        branch=branch,
        visit_date=timezone.now(),
        subjective='Owner reports lethargy',
        objective='T: 38.5°C, HR: 80bpm',
        assessment='Suspected mild infection',
        plan='Amoxicillin 250mg BID x 7 days',
        status='OPEN',
    )


@pytest.fixture
def api_client(vet_user):
    from rest_framework.test import APIClient
    client = APIClient()
    client.force_authenticate(user=vet_user)
    return client
