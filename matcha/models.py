import json
import random
import string

from django.conf import settings
from django.db import models
from django.urls import reverse


class Player(models.Model):
    name = models.CharField(max_length=50)


class Game(models.Model):
    name = models.SlugField(db_index=True)
    players = models.ManyToManyField(Player)

    def get_active_state(self):
        state = self.gamestate_set.all().order_by('-effective').first()
        return state.get_state() if state else None

    def __str__(self):
        return self.name


class GameState(models.Model):
    class Meta:
        unique_together = (('game', 'effective'),)

    game = models.ForeignKey(Game, on_delete=models.PROTECT)
    effective = models.DateTimeField(auto_now_add=True)

    state = models.TextField()

    def get_state(self):
        return json.loads(self.state)

    def __str__(self):
        return "{} {}".format(self.game.name, self.effective)
