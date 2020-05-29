from django.urls import path

from matcha.views import (
    MatchaCreate,
    MatchaDetail,
)

app_name = "matcha"
urlpatterns = [
    path("create/", view=MatchaCreate.as_view(), name="create"),
    path("game/<slug:name>", view=MatchaDetail.as_view(), name="detail"),
]
