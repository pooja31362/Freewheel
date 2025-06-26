# consumers.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer

class StatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("status_group", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("status_group", self.channel_name)

    async def receive(self, text_data):
        # Optional: handle incoming messages from clients
        pass

    async def status_update(self, event):
        await self.send(text_data=json.dumps({
            "user": event["user"],
            "status": event["status"],
        }))
