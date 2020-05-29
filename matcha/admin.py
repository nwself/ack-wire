# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import MatchaGame, MatchaGameState


@admin.register(MatchaGame)
class MatchaGameAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


@admin.register(MatchaGameState)
class MatchaGameStateAdmin(admin.ModelAdmin):
    list_display = ('id', 'game', 'effective', 'state')
    list_filter = ('game', 'effective')
