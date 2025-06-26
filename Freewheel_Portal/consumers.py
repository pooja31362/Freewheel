import json
from channels.generic.websocket import AsyncWebsocketConsumer

class StatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.send(text_data=json.dumps({
            'message': 'Connected successfully'
        }))

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        print(f"Received: {text_data}")
