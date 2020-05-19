from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer

from .models import MatchaGame


class MatchaConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.game_name = self.scope['url_route']['kwargs']['game_name']
        self.user = self.scope['user']
        self.room_group_name = '{}-{}'.format(self.game_name, self.user.pk)

        print("group adding {} {}".format(self.room_group_name, self.channel_name))
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )

        self.accept()

    def disconnect(self, close_code):
        # Leave room group
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    def receive_json(self, content):
        print(content)

        game = MatchaGame.objects.get(name=self.game_name)
        responses = game.process(content, self.user)

        for user, response in responses:
            if user == self.user.pk:
                self.send_json(response)
            else:
                player_room_name = "{}-{}".format(self.game_name, user.pk)

                async_to_sync(self.channel_layer.group_send)(
                    player_room_name,
                    {
                        'type': 'state_message',
                        'state': state
                    }
                )

    def state_message(self, event):
        print("In state_message for {}".format(self.room_group_name))
        message = event['state']

        # Send message to WebSocket
        self.send_json(message)
