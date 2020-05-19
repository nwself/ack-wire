import pytest

from matcha.fsm import Player, Card

@pytest.fixture
def player():
    return Player({
        'name': 'piestastedgood',
        'hand': [Card(Card.Suit.CLUBS, Card.Rank.ACE)],
        'tableau': [Card(Card.Suit.CLUBS, Card.Rank.TEN)],
        'foreplace': [Card(Card.Suit.CLUBS, Card.Rank.KING)],
    }, 0)


def test_init():
    player_name = 'piestastedgood'
    player = Player({
        'name': player_name,
        'hand': [Card(Card.Suit.CLUBS, Card.Rank.ACE)],
        'tableau': [Card(Card.Suit.CLUBS, Card.Rank.TEN)],
    }, 0)
    
    assert(player.name == player_name)
    assert(len(player.hand) == 1)
    assert(len(player.tableau) == 1)


def test_play_card(player: Player):
    starting_hand_length = len(player.hand)
    starting_tableau_length = len(player.tableau)

    card = player.hand[0]

    player.play_card(card)

    assert(len(player.hand) == starting_hand_length - 1)
    assert(len(player.tableau) == starting_tableau_length + 1)

    assert(card not in player.hand)
    assert(card in player.tableau)


def test_last_played(player: Player):
    card = player.hand[0]

    player.play_card(card)
    last_card = player.last_played()

    assert(type(last_card) == Card)
    assert(last_card == card)


def test_to_data(player: Player):
    data = player.to_data()

    assert('name' in data)
    assert(data['name'] == player.name)

    assert('hand' in data)
    assert(len(data['hand']) == len(player.hand))

    assert('tableau' in data)
    assert(len(data['tableau']) == len(player.tableau))

    assert('foreplace' in data)
    assert(len(data['foreplace']) == len(player.foreplace))
