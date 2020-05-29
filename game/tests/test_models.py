import pytest

from game.models import Game

from .factories import GameFactory

pytestmark = pytest.mark.django_db


@pytest.fixture
def game():
    return GameFactory()


def test_model_get_active_state(game: Game):
    assert game.get_active_state() is None
