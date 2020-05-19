from django import forms
from django.contrib import auth
from django.core.exceptions import ValidationError
from django.db.models import Q

from django_select2 import forms as s2forms

from .models import MatchaGame
from game.forms import NotMeWidget


class CreateMatchaForm(forms.ModelForm):
    class Meta:
        model = MatchaGame
        fields = ['name', 'users']

        labels = {
            'name': 'Game Name'
        }

        widgets = {
            'users': NotMeWidget()
        }

    def clean(self):
        users = self.cleaned_data.get('users')
        if users and users.count() != 1:
            raise ValidationError('Maximum one other user allowed.')
