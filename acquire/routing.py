from django.conf.urls import url

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter

from game.consumers import GameConsumer
from matcha.consumers import MatchaConsumer


websocket_urlpatterns = [
    url(r'^ws/chat/(?P<game_pk>[^/]+)/$', GameConsumer),
    url(r'^ws/matcha/(?P<game_name>[^/]+)/$', MatchaConsumer),
]


application = ProtocolTypeRouter({
    # (http->django views is added by default)
    'websocket': AuthMiddlewareStack(
        URLRouter(
            # game.routing.websocket_urlpatterns
            websocket_urlpatterns
        )
    ),
})
