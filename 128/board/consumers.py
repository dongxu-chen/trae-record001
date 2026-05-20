import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Board, Card


class BoardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.board_id = self.scope['url_route']['kwargs']['board_id']
        self.board_group_name = f'board_{self.board_id}'

        await self.channel_layer.group_add(
            self.board_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.board_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message_type = text_data_json.get('type')

        if message_type == 'card_updated':
            card_id = text_data_json['card_id']
            current_version = text_data_json.get('current_version')
            data = text_data_json['data']

            has_conflict = await self.check_version_conflict(card_id, current_version)

            if has_conflict:
                await self.send(text_data=json.dumps({
                    'type': 'conflict_detected',
                    'card_id': card_id,
                    'message': 'Card has been modified by another user. Please refresh and try again.'
                }))
                return

            await self.channel_layer.group_send(
                self.board_group_name,
                {
                    'type': 'card_updated',
                    'card_id': card_id,
                    'data': data,
                }
            )

    @database_sync_to_async
    def check_version_conflict(self, card_id, client_version):
        if client_version is None:
            return False
        try:
            card = Card.objects.get(id=card_id)
            return card.version != client_version
        except Card.DoesNotExist:
            return False

    async def card_moved(self, event):
        await self.send(text_data=json.dumps({
            'type': 'card_moved',
            'card_id': event['card_id'],
            'old_list_id': event['old_list_id'],
            'new_list_id': event['new_list_id'],
            'new_order': event['new_order'],
            'new_version': event.get('new_version'),
        }))

    async def card_updated(self, event):
        await self.send(text_data=json.dumps({
            'type': 'card_updated',
            'card_id': event['card_id'],
            'data': event['data'],
        }))

    async def conflict_detected(self, event):
        await self.send(text_data=json.dumps({
            'type': 'conflict_detected',
            'card_id': event['card_id'],
            'message': event['message'],
        }))
