from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter

from .models import Client
from .serializers import ClientSerializer, ClientListSerializer


class ClientViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['branch', 'preferred_contact', 'is_active']
    search_fields = ['first_name', 'last_name', 'phone', 'whatsapp', 'email', 'id_number']
    ordering_fields = ['last_name', 'first_name', 'created_at']
    ordering = ['last_name', 'first_name']

    def get_serializer_class(self):
        if self.action == 'list':
            return ClientListSerializer
        return ClientSerializer

    def get_queryset(self):
        qs = Client.objects.prefetch_related('pets')
        try:
            branch = self.request.user.staff_profile.branch
            if branch:
                qs = qs.filter(branch=branch)
        except Exception:
            pass
        return qs
