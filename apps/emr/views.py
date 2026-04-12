"""
EMR API views — Consultation CRUD, finalization, multi-file upload.
"""
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from api.permissions import CanFinalizeRecords
from apps.core.utils import write_audit_log
from .models import Consultation, MedicalAttachment
from .serializers import (
    ConsultationSerializer, ConsultationListSerializer, MedicalAttachmentSerializer
)

ALLOWED_CONTENT_TYPES = {
    'image/jpeg', 'image/png', 'image/webp',
    'application/pdf', 'video/mp4',
}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


class ConsultationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'list':
            return ConsultationListSerializer
        return ConsultationSerializer

    def get_queryset(self):
        qs = Consultation.objects.select_related(
            'patient', 'patient__owner', 'attending_vet', 'branch'
        ).prefetch_related('prescriptions', 'attachments')

        patient_id = self.request.query_params.get('patient')
        if patient_id:
            qs = qs.filter(patient_id=patient_id)

        status_f = self.request.query_params.get('status')
        if status_f:
            qs = qs.filter(status=status_f)

        try:
            branch = self.request.user.staff_profile.branch
            if branch:
                qs = qs.filter(branch=branch)
        except Exception:
            pass

        return qs.order_by('-visit_date')

    def perform_create(self, serializer):
        serializer.save(attending_vet=self.request.user)
        write_audit_log(
            user=self.request.user, action='CREATE',
            model_name='Consultation',
            object_id=str(serializer.instance.pk),
            object_repr=str(serializer.instance),
        )

    @action(
        detail=True, methods=['post'], url_path='finalize',
        permission_classes=[IsAuthenticated, CanFinalizeRecords],
    )
    def finalize(self, request, pk=None):
        """Finalize (lock) a consultation. Triggers invoice creation."""
        consultation = self.get_object()
        try:
            consultation.finalize(request.user)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ConsultationSerializer(consultation).data)


class MediaUploadView(APIView):
    """
    Multi-file upload endpoint for clinical photos, lab results, X-rays.
    Supports both camera capture (mobile) and file upload (desktop).
    POST /api/v1/consultations/<id>/upload/
    """

    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    def post(self, request, consultation_id: int):
        consultation = get_object_or_404(
            Consultation, pk=consultation_id, status='OPEN'
        )

        files = request.FILES.getlist('files')
        source = request.data.get('source', 'upload')  # 'camera' | 'upload'
        description = request.data.get('description', '')
        results = []

        for f in files:
            if f.content_type not in ALLOWED_CONTENT_TYPES:
                continue
            if f.size > MAX_FILE_SIZE:
                continue

            attachment = MedicalAttachment.objects.create(
                consultation=consultation,
                file=f,
                file_type=self._detect_type(f.content_type),
                description=description,
                uploaded_by=request.user,
                source_device=request.META.get('HTTP_X_DEVICE_ID', ''),
                is_from_camera=(source == 'camera'),
            )

            # Broadcast to all devices viewing this consultation
            self._notify_attachment(consultation.pk, attachment, request.user)
            results.append({'id': attachment.pk, 'url': attachment.file.url})

        return Response({'uploaded': len(results), 'files': results})

    @staticmethod
    def _detect_type(content_type: str) -> str:
        mapping = {
            'image/jpeg': 'PHOTO', 'image/png': 'PHOTO', 'image/webp': 'PHOTO',
            'application/pdf': 'LAB',
            'video/mp4': 'VIDEO',
        }
        return mapping.get(content_type, 'DOC')

    @staticmethod
    def _notify_attachment(consultation_id: int, attachment, user) -> None:
        try:
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f'consultation_{consultation_id}',
                {
                    'type': 'attachment_added',
                    'attachment_id': attachment.pk,
                    'filename': attachment.file.name.split('/')[-1],
                    'uploaded_by': user.get_full_name(),
                    'consultation_id': consultation_id,
                },
            )
        except Exception:
            pass  # WS failure must never break file upload
