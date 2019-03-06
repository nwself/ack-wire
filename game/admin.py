from django.contrib import admin

from . import models

@admin.register(models.Game)
class GameAdmin(admin.ModelAdmin):
    # list_display = ["id", "description"]
    pass


@admin.register(models.GameState)
class GameStateAdmin(admin.ModelAdmin):
    list_display = ["game", "effective"]
    pass
