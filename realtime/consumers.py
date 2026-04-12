"""
Django Channels WebSocket consumers.

ClinicConsumer     — branch-wide hub: appointments, inventory, billing events
ConsultationConsumer — per-consultation room: collaborative editing notifications
"""
import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class ClinicConsumer(AsyncWebsocketConsumer):
    """
    Main real-time hub for the clinic floor.
    Group: clinic_{branch_id} — all devices in the same branch.

    Events handled:
      appointment.status_changed  → refresh appointment card
      inventory.low_stock         → show alert badge
      inventory.expiry_alert      → show expiry warning
      invoice.paid                → refresh revenue widget
      consultation.new_attachment → refresh file list
    """

    async def connect(self) -> None:
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        self.branch_id = await self._get_branch_id()
        if not self.branch_id:
            await self.close()
            return

        self.group_name = f'clinic_{self.branch_id}'

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await self.send(text_data=json.dumps({
            'type': 'connection.established',
            'branch_id': self.branch_id,
            'user': self.user.get_full_name(),
        }))
        logger.debug('WS connect: %s → %s', self.user, self.group_name)

    async def disconnect(self, code: int) -> None:
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
        logger.debug('WS disconnect: %s', self.user)

    async def receive(self, text_data: str) -> None:
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        event_type = data.get('type', '')

        handlers = {
            'ping': self._handle_ping,
        }

        handler = handlers.get(event_type)
        if handler:
            await handler(data)

    async def _handle_ping(self, data: dict) -> None:
        await self.send(text_data=json.dumps({'type': 'pong'}))

    # ── Group message handlers ─────────────────────────────────────────
    # Django Channels calls these when a group_send() targets this consumer.
    # Method names: dots in type → underscores (e.g. appointment.status_changed → appointment_status_changed)

    async def appointment_status_changed(self, event: dict) -> None:
        await self.send(text_data=json.dumps({
            'type': 'appointment.status_changed',
            'appointment_id': event['appointment_id'],
            'new_status': event['new_status'],
            'patient_name': event['patient_name'],
            'updated_by': event['updated_by'],
            'timestamp': event['timestamp'],
        }))

    async def inventory_low_stock(self, event: dict) -> None:
        await self.send(text_data=json.dumps({
            'type': 'inventory.low_stock',
            'item_id': event['item_id'],
            'item_name': event['item_name'],
            'current_qty': event['current_qty'],
            'reorder_level': event['reorder_level'],
        }))

    async def inventory_expiry_alert(self, event: dict) -> None:
        await self.send(text_data=json.dumps({
            'type': 'inventory.expiry_alert',
            'item_id': event['item_id'],
            'item_name': event['item_name'],
            'expiry_date': event['expiry_date'],
            'days_remaining': event['days_remaining'],
            'severity': event['severity'],
        }))

    async def invoice_paid(self, event: dict) -> None:
        await self.send(text_data=json.dumps({
            'type': 'invoice.paid',
            'invoice_number': event['invoice_number'],
            'amount': event['amount'],
            'patient_name': event['patient_name'],
            'payment_method': event['payment_method'],
        }))

    async def consultation_attachment_added(self, event: dict) -> None:
        await self.send(text_data=json.dumps({
            'type': 'consultation.new_attachment',
            'consultation_id': event.get('consultation_id'),
            'attachment_id': event['attachment_id'],
            'filename': event['filename'],
            'uploaded_by': event['uploaded_by'],
        }))

    # ── DB helpers ─────────────────────────────────────────────────────

    @database_sync_to_async
    def _get_branch_id(self) -> int | None:
        try:
            return self.user.staff_profile.branch_id
        except Exception:
            return None


class ConsultationConsumer(AsyncWebsocketConsumer):
    """
    Per-consultation WebSocket room.
    All devices viewing the same consultation record join this group.

    Enables:
    - Real-time "someone is editing" awareness
    - Immediate attachment upload notifications
    - Field-level typing indicators (optional UX enhancement)
    """

    async def connect(self) -> None:
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        self.consultation_pk = self.scope['url_route']['kwargs']['pk']
        self.group = f'consultation_{self.consultation_pk}'

        # Verify the consultation is accessible
        accessible = await self._can_access()
        if not accessible:
            await self.close()
            return

        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

        # Notify others someone joined
        await self.channel_layer.group_send(self.group, {
            'type': 'editor_joined',
            'user': self.user.get_full_name(),
            'exclude': self.channel_name,
        })

    async def disconnect(self, code: int) -> None:
        if hasattr(self, 'group'):
            await self.channel_layer.group_discard(self.group, self.channel_name)
            await self.channel_layer.group_send(self.group, {
                'type': 'editor_left',
                'user': self.user.get_full_name(),
            })

    async def receive(self, text_data: str) -> None:
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        if data.get('type') == 'field.update':
            # Broadcast typing/field update to other viewers (exclude sender)
            await self.channel_layer.group_send(self.group, {
                'type': 'field_updated',
                'field': data.get('field'),
                'value': data.get('value'),
                'by': self.user.get_full_name(),
                'exclude': self.channel_name,
            })

    # ── Group handlers ─────────────────────────────────────────────────

    async def editor_joined(self, event: dict) -> None:
        if event.get('exclude') == self.channel_name:
            return
        await self.send(text_data=json.dumps({
            'type': 'editor.joined',
            'user': event['user'],
        }))

    async def editor_left(self, event: dict) -> None:
        await self.send(text_data=json.dumps({
            'type': 'editor.left',
            'user': event['user'],
        }))

    async def field_updated(self, event: dict) -> None:
        if event.get('exclude') == self.channel_name:
            return
        await self.send(text_data=json.dumps({
            'type': 'field.updated',
            'field': event['field'],
            'value': event['value'],
            'by': event['by'],
        }))

    async def attachment_added(self, event: dict) -> None:
        await self.send(text_data=json.dumps({
            'type': 'consultation.new_attachment',
            'attachment_id': event['attachment_id'],
            'filename': event['filename'],
            'uploaded_by': event['uploaded_by'],
        }))

    @database_sync_to_async
    def _can_access(self) -> bool:
        from apps.emr.models import Consultation
        try:
            Consultation.objects.get(pk=self.consultation_pk)
            return True
        except Consultation.DoesNotExist:
            return False
