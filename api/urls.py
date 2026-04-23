"""
DRF API v1 URL configuration.
All routes are under /api/v1/
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.clients.views import ClientViewSet
from apps.patients.views import PatientViewSet, WeightRecordViewSet, VaccinationViewSet
from apps.emr.views import ConsultationViewSet, MediaUploadView
from apps.inventory.views import InventoryItemViewSet, StockTransactionViewSet
from apps.billing.views import InvoiceViewSet
from apps.appointments.views import AppointmentViewSet
from apps.analytics.views import (
    RevenueReportView, InventoryForecastView, DashboardStatsView
)
from frontend.views import GlobalSearchView, MediaAuthView
from apps.core.cds_views import CdsCaseListView, CdsCaseDetailView

router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'patients', PatientViewSet, basename='patient')
router.register(r'weight-records', WeightRecordViewSet, basename='weight')
router.register(r'vaccinations', VaccinationViewSet, basename='vaccination')
router.register(r'consultations', ConsultationViewSet, basename='consultation')
router.register(r'inventory', InventoryItemViewSet, basename='inventory')
router.register(r'stock-transactions', StockTransactionViewSet, basename='stock-tx')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'appointments', AppointmentViewSet, basename='appointment')

urlpatterns = [
    # JWT auth
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Global search (optimised for 20 concurrent devices)
    path('search/', GlobalSearchView.as_view(), name='global_search'),

    # Media auth (Nginx internal auth_request)
    path('media-auth/', MediaAuthView.as_view(), name='media_auth'),

    # Multi-file upload for EMR
    path('consultations/<int:consultation_id>/upload/',
         MediaUploadView.as_view(), name='media_upload'),

    # Analytics
    path('reports/revenue/', RevenueReportView.as_view(), name='revenue_report'),
    path('reports/dashboard/', DashboardStatsView.as_view(), name='dashboard_stats'),
    path('inventory/forecast/', InventoryForecastView.as_view(), name='inventory_forecast'),

    # CDS offline tool sync (key-based auth, CORS-safe from file://)
    path('cds/cases/', CdsCaseListView.as_view(), name='cds_cases'),
    path('cds/cases/<int:case_id>/', CdsCaseDetailView.as_view(), name='cds_case_detail'),

    # ViewSet routes
    path('', include(router.urls)),
]
