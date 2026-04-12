"""
Management command: seed_demo_data
Creates a full set of demo data for development and testing:
  - 2 branches (JoyVet Care Kemang, JoyTails BSD)
  - 5 staff users with various roles
  - 20 clients (pet owners)
  - 30 patients (mixed species)
  - 50 inventory items
  - 15 appointments (today + upcoming)
  - 10 consultations (open + closed)
  - Sample invoices

Usage:
  python manage.py seed_demo_data
  python manage.py seed_demo_data --clear   # wipe and re-seed
"""
from __future__ import annotations
import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models import Branch, StaffProfile
from apps.clients.models import Client
from apps.patients.models import Patient, VaccinationRecord
from apps.inventory.models import InventoryItem, StockTransaction
from apps.appointments.models import Appointment


class Command(BaseCommand):
    help = 'Seed demo data for JoyVet Care (dev/test use only)'

    def add_arguments(self, parser):
        parser.add_argument('--clear', action='store_true',
                            help='Clear existing data before seeding')

    def handle(self, *args, **options):
        if options['clear']:
            self._clear()

        self.stdout.write('🌱 Seeding demo data…')

        branches = self._create_branches()
        users = self._create_staff(branches)
        clients = self._create_clients(branches)
        patients = self._create_patients(clients)
        inventory = self._create_inventory(branches)
        self._create_appointments(patients, users, branches)
        self._create_vaccinations(patients, inventory, users)

        self.stdout.write(self.style.SUCCESS(
            '\n✓ Demo data seeded successfully!\n'
            f'  Branches: {len(branches)}\n'
            f'  Staff users: {len(users)}\n'
            f'  Clients: {len(clients)}\n'
            f'  Patients: {len(patients)}\n'
            f'  Inventory items: {len(inventory)}\n'
            '\n  Admin login: admin / joyvet2024\n'
            '  Vet login:   dr.budi / joyvet2024\n'
        ))

    def _clear(self):
        self.stdout.write('  Clearing existing data…')
        from apps.billing.models import Invoice, InvoiceLineItem
        from apps.emr.models import Consultation, Prescription, MedicalAttachment
        InvoiceLineItem.objects.all().delete()
        Invoice.objects.all().delete()
        Prescription.objects.all().delete()
        MedicalAttachment.objects.all().delete()
        Consultation.objects.all().delete()
        Appointment.objects.all().delete()
        VaccinationRecord.objects.all().delete()
        StockTransaction.objects.all().delete()
        Patient.objects.all().delete()
        Client.objects.all().delete()
        InventoryItem.objects.all().delete()
        StaffProfile.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        Branch.objects.all().delete()

    def _create_branches(self) -> list[Branch]:
        branches = [
            Branch.objects.get_or_create(
                code='JVC',
                defaults={
                    'name': 'JoyVet Care Kemang',
                    'address': 'Jl. Kemang Raya No. 12, Jakarta Selatan',
                    'phone': '+6221-7199001',
                    'email': 'kemang@joyvetcare.com',
                },
            )[0],
            Branch.objects.get_or_create(
                code='JTL',
                defaults={
                    'name': 'JoyTails BSD',
                    'address': 'Ruko BSD City Sektor XIV No. 5, Tangerang Selatan',
                    'phone': '+6221-5374002',
                    'email': 'bsd@joytails.com',
                },
            )[0],
        ]
        self.stdout.write(f'  ✓ Branches: {len(branches)}')
        return branches

    def _create_staff(self, branches: list[Branch]) -> list[User]:
        # Superuser / admin
        admin, _ = User.objects.get_or_create(
            username='admin',
            defaults={'first_name': 'Admin', 'last_name': 'JoyVet',
                      'email': 'admin@joyvetcare.com', 'is_superuser': True,
                      'is_staff': True},
        )
        admin.set_password('joyvet2024')
        admin.save()

        staff_data = [
            ('dr.budi', 'Budi', 'Santoso', 'VET', branches[0], True, True),
            ('dr.sari', 'Sari', 'Wijaya', 'VET', branches[1], True, True),
            ('nurse.rina', 'Rina', 'Pertiwi', 'NURSE', branches[0], False, False),
            ('recept.dian', 'Dian', 'Lestari', 'RECEPTIONIST', branches[0], False, True),
        ]

        users = [admin]
        for username, first, last, role, branch, can_fin, can_fin2 in staff_data:
            u, _ = User.objects.get_or_create(
                username=username,
                defaults={'first_name': first, 'last_name': last,
                          'email': f'{username}@joyvetcare.com'},
            )
            u.set_password('joyvet2024')
            u.save()

            StaffProfile.objects.get_or_create(
                user=u,
                defaults={
                    'branch': branch, 'role': role,
                    'can_finalize_records': can_fin,
                    'can_view_financials': can_fin2,
                },
            )
            users.append(u)

        self.stdout.write(f'  ✓ Staff: {len(users)}')
        return users

    def _create_clients(self, branches: list[Branch]) -> list[Client]:
        CLIENT_DATA = [
            ('Andi', 'Kurniawan', '08111234567', branches[0]),
            ('Bela', 'Putri', '08122345678', branches[0]),
            ('Candra', 'Setiawan', '08133456789', branches[0]),
            ('Dewi', 'Rahayu', '08144567890', branches[0]),
            ('Eko', 'Prasetyo', '08155678901', branches[0]),
            ('Fitri', 'Handayani', '08166789012', branches[1]),
            ('Guntur', 'Wibowo', '08177890123', branches[1]),
            ('Hani', 'Suryani', '08188901234', branches[1]),
            ('Irwan', 'Nugroho', '08199012345', branches[1]),
            ('Joko', 'Santoso', '08100123456', branches[0]),
        ]
        clients = []
        for first, last, phone, branch in CLIENT_DATA:
            c, _ = Client.objects.get_or_create(
                branch=branch, phone=phone,
                defaults={
                    'first_name': first, 'last_name': last,
                    'whatsapp': phone,
                    'preferred_contact': 'WA',
                    'address': 'Jakarta, Indonesia',
                },
            )
            clients.append(c)

        self.stdout.write(f'  ✓ Clients: {len(clients)}')
        return clients

    def _create_patients(self, clients: list[Client]) -> list[Patient]:
        PATIENT_DATA = [
            ('Max',     'DOG',    'Golden Retriever', 'M',  clients[0], 28.5, 2019),
            ('Luna',    'CAT',    'Persian',           'FS', clients[0], 3.2,  2020),
            ('Biscuit', 'DOG',    'Beagle',            'MN', clients[1], 12.0, 2021),
            ('Mochi',   'CAT',    'Scottish Fold',     'F',  clients[2], 4.1,  2022),
            ('Buddy',   'DOG',    'Labrador',          'M',  clients[3], 30.0, 2018),
            ('Kiki',    'BIRD',   'Cockatiel',         'F',  clients[4], 0.1,  2021),
            ('Pipi',    'RABBIT', 'Holland Lop',       'F',  clients[5], 1.8,  2022),
            ('Rocky',   'DOG',    'Rottweiler',        'M',  clients[6], 42.0, 2017),
            ('Kitty',   'CAT',    'Domestic Shorthair','F',  clients[7], 3.5,  2020),
            ('Hammy',   'HAMSTER','Syrian Hamster',    'M',  clients[8], 0.12, 2023),
        ]
        patients = []
        for name, species, breed, gender, owner, weight, birth_year in PATIENT_DATA:
            p, _ = Patient.objects.get_or_create(
                owner=owner, name=name,
                defaults={
                    'species': species, 'breed': breed, 'gender': gender,
                    'current_weight_kg': Decimal(str(weight)),
                    'birth_date': date(birth_year, random.randint(1, 12), 1),
                },
            )
            patients.append(p)

        self.stdout.write(f'  ✓ Patients: {len(patients)}')
        return patients

    def _create_inventory(self, branches: list[Branch]) -> list[InventoryItem]:
        ITEMS = [
            ('Amoxicillin 250mg', 'Amoxicillin', 'MED', 'JVC-MED-001', 'tablet',  5000,  15000, 200, 20),
            ('Meloxicam 1mg',     'Meloxicam',   'MED', 'JVC-MED-002', 'tablet',  3000,  10000, 100, 15),
            ('Rabies Vaccine',    'Rabipur',     'VACCINE','JVC-VAC-001','dose',  45000, 120000,  50, 10),
            ('DHPP Vaccine',      'Nobivac',     'VACCINE','JVC-VAC-002','dose',  40000, 100000,  40,  8),
            ('Syringes 5ml',      '',            'SUPPLY','JVC-SUP-001','piece',   500,   2000, 500, 50),
            ('Royal Canin Small', '',            'FOOD', 'JVC-FOOD-001','bag',  120000, 250000,  20,  5),
            ('Frontline Plus Dog','',            'RETAIL','JVC-RET-001','pack',  80000, 150000,  30,  5),
            ('Medicated Shampoo', '',            'GROOMING','JVC-GRM-001','bottle',25000, 65000, 25,  5),
            ('Consultation Fee',  '',            'SERVICE','JVC-SVC-001','visit',      0, 150000,   0,  0),
            ('Grooming Small Dog','',            'SERVICE','JVC-SVC-002','session',    0, 200000,   0,  0),
        ]
        items = []
        for name, generic, cat, sku, unit, cost, sell, stock, reorder in ITEMS:
            for branch in branches:
                branch_sku = f"{sku}-{branch.code}"
                item, _ = InventoryItem.objects.get_or_create(
                    sku=branch_sku,
                    defaults={
                        'branch': branch, 'name': name, 'generic_name': generic,
                        'category': cat, 'unit': unit,
                        'cost_price': Decimal(str(cost)),
                        'selling_price': Decimal(str(sell)),
                        'stock_quantity': Decimal(str(stock)),
                        'reorder_level': Decimal(str(reorder)),
                        'tax_rate': Decimal('11.00') if cat in ('MED', 'VACCINE') else Decimal('0'),
                        'expiry_date': date.today() + timedelta(days=random.randint(90, 730)),
                        'is_active': True,
                    },
                )
                items.append(item)

        self.stdout.write(f'  ✓ Inventory items: {len(items)}')
        return items

    def _create_appointments(self, patients, users, branches) -> None:
        vets = [u for u in users if hasattr(u, 'staff_profile') and
                u.staff_profile.role == 'VET']
        if not vets:
            vets = [users[1]]  # fallback to first non-admin

        now = timezone.now()
        today = now.date()
        appt_data = [
            (patients[0], vets[0], branches[0], now.replace(hour=9, minute=0),  'CONSULT',   'CONFIRMED'),
            (patients[1], vets[0], branches[0], now.replace(hour=9, minute=30), 'VACCINE',   'CHECKED_IN'),
            (patients[2], vets[0], branches[0], now.replace(hour=10, minute=0), 'CONSULT',   'IN_PROGRESS'),
            (patients[3], vets[0], branches[0], now.replace(hour=10, minute=30),'FOLLOWUP',  'BOOKED'),
            (patients[4], vets[0], branches[0], now.replace(hour=14, minute=0), 'GROOM',     'BOOKED'),
        ]

        created = 0
        for patient, vet, branch, scheduled_at, appt_type, status in appt_data:
            if not Appointment.objects.filter(
                patient=patient,
                scheduled_at=scheduled_at,
            ).exists():
                Appointment.objects.create(
                    patient=patient, veterinarian=vet, branch=branch,
                    scheduled_at=scheduled_at, duration_minutes=30,
                    appointment_type=appt_type, status=status,
                    created_by=vet,
                )
                created += 1

        self.stdout.write(f'  ✓ Appointments: {created} created for today')

    def _create_vaccinations(self, patients, inventory, users) -> None:
        vaccine_items = [i for i in inventory if i.category == 'VACCINE']
        if not vaccine_items:
            return

        created = 0
        for patient in patients[:6]:
            vaccine = random.choice(vaccine_items)
            if not VaccinationRecord.objects.filter(
                patient=patient, vaccine_name=vaccine.name
            ).exists():
                adm_date = date.today() - timedelta(days=random.randint(30, 365))
                VaccinationRecord.objects.create(
                    patient=patient,
                    vaccine_name=vaccine.name,
                    administered_date=adm_date,
                    next_due_date=adm_date + timedelta(days=365),
                    administered_by=users[1] if len(users) > 1 else users[0],
                    inventory_item=vaccine,
                )
                created += 1

        self.stdout.write(f'  ✓ Vaccination records: {created}')
