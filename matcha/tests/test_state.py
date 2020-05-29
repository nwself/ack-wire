import pytest

from matcha.fsm import Card, Player, State


@pytest.fixture
def player():
    return Player({
        'name': 'piestastedgood',
        'hand': [Card(Card.Suit.CLUBS, Card.Rank.ACE)],
        'tableau': [Card(Card.Suit.CLUBS, Card.Rank.TEN)],
        'foreplace': [Card(Card.Suit.CLUBS, Card.Rank.KING)],
    }, 0)


def test_to_data(player: Player):
    state = State(player, 'lead', 0)
    data = state.to_data()

    assert('player' in data)
    assert(type(data['player']) == str)
    assert(data['player'] == player.name)
    assert('state' in data)
    assert('game_id' in data)
