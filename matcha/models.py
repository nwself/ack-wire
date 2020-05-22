import json

from django.conf import settings
from django.db import models
from django.urls import reverse

from .fsm import MatchaState


class MatchaGame(models.Model):
    name = models.SlugField(db_index=True)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL)

    # rollback last turn/delete most recent game state
    # matcha_game.matchagamestate_set.all().order_by('-effective').first().delete()

    def get_absolute_url(self):
        return reverse('matcha:detail', kwargs={'name': self.name})

    def get_active_state(self, for_=None):
        state = self.matchagamestate_set.all().order_by('-effective').first()
        if not state:
            return None

        state = state.get_state(for_=for_)
        state['game_name'] = self.name

        return state

    def start_game(self):
        state = MatchaState({'players': [
            {'name': u.username} for u in self.users.all()
        ]})
        state.initialize()
        self.matchagamestate_set.create(state=json.dumps(state.to_data()))

    def process(self, data, user):
        print(f"Process this {data}")

        if data['action'] == 'get_state':
            return [(user.pk, self.get_active_state(for_=user))]

        state = MatchaState.from_data(self.get_active_state())
        if not hasattr(state, data['action']):
            raise ActionForbiddenException(f"No such action {data['action']}")

        getattr(state, data['action'])(data['body'])
        db_state = self.matchagamestate_set.create(state=json.dumps(state.to_data()))

        return [(user.pk, db_state.get_state(for_=user)) for user in self.users.all()]

    def __str__(self):
        return self.name


class MatchaGameState(models.Model):
    class Meta:
        unique_together = (('game', 'effective'),)

    game = models.ForeignKey(MatchaGame, on_delete=models.PROTECT)
    effective = models.DateTimeField(auto_now_add=True)

    state = models.TextField()

    def get_state(self, for_=None):
        state = json.loads(self.state)

        if for_ is None:
            return state

        for player in state['players']:
            if player['name'] != for_.username:
                del player['hand']
        state['me'] = for_.username

        return state

    def __str__(self):
        return "{} {}".format(self.game.name, self.effective)
