import copy
import json
import logging

from asgiref.sync import async_to_sync
from channels.generic.websocket import JsonWebsocketConsumer

from .views import PlayTileAction, DeclareChainAction, BuyStocksAction, DisposeStockAction, DetermineWinnerAction, EndGameAction, ActionForbiddenException


logger = logging.getLogger(__file__)


class GameConsumer(JsonWebsocketConsumer):
    def connect(self):
        self.game_pk = self.scope['url_route']['kwargs']['game_pk']
        self.user = self.scope['user']
        self.room_group_name = '{}-{}'.format(self.game_pk, self.user.username)

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

        try:
            action = None
            if content['action'] == 'play_tile':
                print("{} {} {}".format(self.game_pk, self.user, content['body']['tile']))
                action = PlayTileAction(self.game_pk, self.user, content['body']['tile'])
                # new_state = play_tile(self.game_pk, self.user, content['body']['tile'])
            elif content['action'] == 'declare_chain':
                print("{} {} {}".format(self.game_pk, self.user, content['body']['chain']))
                action = DeclareChainAction(self.game_pk, self.user, content['body']['chain'])
            elif content['action'] == 'buy_stocks':
                print("{} {} {}".format(self.game_pk, self.user, content['body']['stocks']))
                action = BuyStocksAction(self.game_pk, self.user, content['body']['stocks'])
            elif content['action'] == 'dispose_stocks':
                print("{} {} {}".format(self.game_pk, self.user, content['body']['cart']))
                action = DisposeStockAction(self.game_pk, self.user, content['body']['cart'])
            elif content['action'] == 'determine_winner':
                print("{} {} {}".format(self.game_pk, self.user, content['body']['chains']))
                action = DetermineWinnerAction(self.game_pk, self.user, content['body']['chains'])
            elif content['action'] == 'end_game':
                print("{} {} end_game".format(self.game_pk, self.user))
                action = EndGameAction(self.game_pk, self.user)
            else:
                logger.error("In receive got unknown action {} body {}".format(content['action'], content['body']))

            new_state = action.process() if action else {}
        except ActionForbiddenException:
            new_state = {"status": 403}

        players = copy.deepcopy(new_state['players'])
        for player in players:
            new_state['players'] = copy.deepcopy(players)
            for i, p in enumerate(new_state['players']):
                if player['username'] != p['username']:
                    del p['tiles']

            player_room_name = "{}-{}".format(self.game_pk, player['username'])

            print("Trying to group_send to {}".format(player_room_name))
            async_to_sync(self.channel_layer.group_send)(
                player_room_name,
                {
                    'type': 'state_message',
                    'state': new_state
                }
            )


    # Receive message from room group
    def state_message(self, event):
        print("In state_message for {}".format(self.room_group_name))
        message = event['state']

        # Send message to WebSocket
        self.send_json(message)


# class ChatConsumer(WebsocketConsumer):
#     def connect(self):
#         self.room_name = self.scope['url_route']['kwargs']['room_name']
#         self.room_group_name = 'chat_%s' % self.room_name
#         self.user = self.scope["user"]

#         # Join room group
#         async_to_sync(self.channel_layer.group_add)(
#             self.room_group_name,
#             self.channel_name
#         )

#         self.accept()

#     def disconnect(self, close_code):
#         # Leave room group
#         async_to_sync(self.channel_layer.group_discard)(
#             self.room_group_name,
#             self.channel_name
#         )

#     # Receive message from WebSocket
#     def receive(self, text_data):
#         print(text_data)
#         text_data_json = json.loads(text_data)

#         action = text_data_json['action']
#         body = text_data_json['body']

#         if action == 'play_tile':
#             print("{} {} {}".format(self.room_name, self.user, body['tile']))
#             new_state = play_tile(self.room_name, self.user, body['tile'])
#         else:
#             logger.error("In receive got unknown action {} body {}".format(action, body))

#         print(new_state)
#         # Send action to room group
#         async_to_sync(self.channel_layer.group_send)(
#             self.room_group_name,
#             {
#                 'type': 'chat_message',
#                 'action': action,
#                 'new_state': json.dumps(new_state),
#             }
#         )

#     # Receive message from room group
#     def chat_message(self, event):
#         message = event['message']

#         # Send message to WebSocket
#         self.send(text_data=json.dumps({
#             'message': message
#         }))
