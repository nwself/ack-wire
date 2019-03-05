from django.conf import settings
from django.db import models


class Game(models.Model):
    name = models.SlugField(db_index=True)
    users = models.ManyToManyField(settings.AUTH_USER_MODEL)
