"""HTMX frontend URL routing."""
from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('dashboard/revenue-widget/', views.revenue_widget, name='revenue_widget'),

    # Patients
    path('patients/', views.patient_list, name='patient_list'),
    path('patients/<int:pk>/', views.patient_detail, name='patient_detail'),

    # Appointments
    path('appointments/<int:pk>/card/', views.appointment_card, name='appointment_card'),
    path('appointments/<int:pk>/status/', views.appointment_status_update,
         name='appointment_status'),

    # EMR
    path('emr/consultations/<int:pk>/', views.consultation_detail,
         name='consultation_detail'),

    # Inventory
    path('inventory/', views.inventory_list, name='inventory_list'),
    path('inventory/forecast/', views.inventory_forecast_fragment, name='inventory_forecast'),
]
