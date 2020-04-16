from django import forms

from .models import Game

# This is currently unused, the CreateGame view in views makes its own form class 
# via inheritance in Django code
class GameForm(forms.ModelForm):
    class Meta:
        model = Game
        fields = ['name', 'users', 'double_tiles_variant']
