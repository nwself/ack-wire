from django import forms
from django.contrib import auth
from django.db.models import Q

from django_select2 import forms as s2forms

from .models import Game


class NotMeWidget(s2forms.ModelSelect2MultipleWidget):
    model = auth.get_user_model()
    search_fields = ['username__istartswith']

    def filter_queryset(self, request, term, queryset, **kwargs):
        return super().filter_queryset(request, term, queryset, **kwargs).filter(
            ~Q(username=request.user.username)
        )


class GameForm(forms.ModelForm):
    class Meta:
        model = Game
        fields = ['name', 'users', 'double_tiles_variant', 'no_2player_tile_draw_variant']

        labels = {
            'name': 'Game Name'
        }

        widgets = {
            'users': NotMeWidget()
        }
