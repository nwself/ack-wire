import pytest

from matcha.fsm import DoubleMatchaState, Card

@pytest.fixture
def state():
    s = DoubleMatchaState({
        'players': [
            {'name': 'piestastedgood'},
            {'name': 'tripswithtires'}
        ]
    })
    s.initialize()
    return s


def test_initialize():
    state = DoubleMatchaState({
        'players': [
            {'name': 'piestastedgood'},
            {'name': 'tripswithtires'}
        ]
    })
    state.initialize()
    assert len(state.players[0].hand) == 10
    assert len(state.players[1].hand) == 10


def test_to_data(state: DoubleMatchaState):
    data = state.to_data()

    assert 'players' in data
    assert 'state' in data


def test_to_data_state_players(state: DoubleMatchaState):
    data = state.to_data()

    assert len(data['players']) == 2
    for player in data['players']:
        assert 'name' in player
        assert 'hand' in player
        assert 'tableau' in player


def test_to_data_state(state: DoubleMatchaState):
    data = state.to_data()

    assert 'state' in data['state']
    assert 'player' in data['state']
    assert type(data['state']['player']) == str


def test_next_player(state: DoubleMatchaState):
    assert(state.next_player() == state.players[1])


def test_lead(state: DoubleMatchaState):
    card = state.state.player.hand[0]
    card_data = card.to_data()

    state.lead(card_data)

    assert(state.state.state_name == 'follow')
    assert(state.state.player == state.players[1])


def test_valid_follow_suit(state: DoubleMatchaState):
    lead_card = Card(Card.Suit.CLUBS, Card.Rank.KING)
    follow_card = Card(Card.Suit.CLUBS, Card.Rank.QUEEN)

    state.current_player().hand = [lead_card]
    state.next_player().hand = [follow_card]

    state.lead(lead_card.to_data())

    assert(state.valid_follow(follow_card) == True)


def test_valid_follow_rank(state: DoubleMatchaState):
    lead_card = Card(Card.Suit.CLUBS, Card.Rank.KING)
    follow_card = Card(Card.Suit.HEARTS, Card.Rank.KING)

    state.current_player().hand = [lead_card]
    state.next_player().hand = [follow_card]

    state.lead(lead_card.to_data())

    assert(state.valid_follow(follow_card) == True)


def test_valid_follow_rank_but_suit(state: DoubleMatchaState):
    lead_card = Card(Card.Suit.CLUBS, Card.Rank.KING)
    follow_card = Card(Card.Suit.HEARTS, Card.Rank.KING)

    state.current_player().hand = [lead_card]
    state.next_player().hand = [follow_card, Card(Card.Suit.CLUBS, Card.Rank.SEVEN)]

    state.lead(lead_card.to_data())

    assert(state.valid_follow(follow_card) == False)


def test_follow_lower_card(state: DoubleMatchaState):
    lead_card = Card(Card.Suit.CLUBS, Card.Rank.KING)
    follow_card = Card(Card.Suit.CLUBS, Card.Rank.QUEEN)

    starting_player = state.current_player()

    state.current_player().hand[0] = lead_card
    state.next_player().hand[0] = follow_card

    # player[0] leads ♣K
    state.lead(lead_card.to_data())

    # player[1] follows ♣Q
    state.follow(follow_card.to_data())

    assert(state.state.state_name == 'lead')
    assert(state.state.player == starting_player)

    assert(follow_card not in state.next_player().hand)
    assert(follow_card in state.next_player().tableau)


def test_follow_higher_card(state: DoubleMatchaState):
    lead_card = Card(Card.Suit.CLUBS, Card.Rank.KING)
    follow_card = Card(Card.Suit.CLUBS, Card.Rank.TEN)

    following_player = state.next_player()

    state.current_player().hand[0] = lead_card
    state.next_player().hand[0] = follow_card

    state.lead(lead_card.to_data())
    state.follow(follow_card.to_data())

    assert(state.state.state_name == 'lead')
    assert(state.state.player == following_player)


def test_follow_same_card(state: DoubleMatchaState):
    lead_card = Card(Card.Suit.DIAMONDS, Card.Rank.ACE)
    follow_card = Card(Card.Suit.DIAMONDS, Card.Rank.ACE)

    leading_player = state.current_player()

    state.current_player().hand[0] = lead_card
    state.next_player().hand[0] = follow_card

    state.lead(lead_card.to_data())
    state.follow(follow_card.to_data())

    assert(state.state.state_name == 'lead')
    assert(state.state.player == leading_player)


def test_foreplace(state: DoubleMatchaState):
    state.foreplace(state.current_player().hand[0].to_data())

    assert(state.state.state_name == 'foreplace')
    assert(state.state.player == state.players[1])

    state.foreplace(state.current_player().hand[0].to_data())

    assert(state.state.state_name == 'lead')
    assert(state.state.player == state.players[0])


def test_end_game(state: DoubleMatchaState):
    lead_card = Card(Card.Suit.CLUBS, Card.Rank.KING)
    follow_card = Card(Card.Suit.HEARTS, Card.Rank.KING)

    state.current_player().hand = [lead_card]
    state.next_player().hand = [follow_card]

    state.lead(lead_card.to_data())
    state.follow(follow_card.to_data())

    assert(state.state.state_name == 'game_end')
