import pytest

from matcha.game import MatchaGame
from matcha.fsm import Card


@pytest.fixture
def game():
    return MatchaGame()


def test_init():
    game = MatchaGame()
    assert(game is not None)
    assert(game.state == 'uninitialized')


def test_initialize(game: MatchaGame):
    game.initialize()

    assert(game.state == 'foreplace')
    assert(len(game.deck) == 20)
    assert(type(game.deck[0]) == Card)
