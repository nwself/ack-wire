from django.db import models
from django.forms import ModelForm

from .models import Game

class GameForm(ModelForm):
        class Meta:
                    model = Game
                            fields = ['name', 'users']

