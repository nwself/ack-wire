import string

from django.conf import settings
from django.db import models


class Game(models.Model):
    name = models.SlugField(db_index=True)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL)


class GameState(models.Model):
    class Meta:
        unique_together = (('game', 'effective'),)

    game = models.ForeignKey(Game, on_delete=models.PROTECT)
    effective = models.DateTimeField(auto_now_add=True)

    state = models.TextField()


def build_initial_state(users, chains=None, rows=9, columns=12, starting_stocks=25):
    if chains is None:
        chains = ["Luxor", "Tower", "American", "Festival", "Worldwide", "Continental", "Imperial"]

    return {
        'chains': {c: 0 for c in chains},
        'assignments': {},   # will look like "A10": "Festival"
        'players': {user.username: {
            'cash': 500,
            'stocks': {},
            'tiles': [],
        } for user in users},       # clients shouldn't have all of this
        'supply': {      # clients shouldn't have this
            'stocks': {c: starting_stocks for c in chains},
            'tiles': [
                [
                    string.ascii_uppercase[i] + str(j + 1) for j in range(0, columns)
                ] for i in range(0, rows)
            ]
        },
        'merging_chains': [],  # only on state if a merge is active
        'defunct_chains': [],  # needed to resolve merger since merging_chains will be mutated
        'merging_player': "",
        'active_cell': "",  # used for recently placed tile
        'game': "",  # the game_name slug
        'state': {
            'player': "",
            'state': ""    # this is state.state.state which is a stupid thing to call something
        },
        'end_game': False     # used to end game when a player calls it
    }
