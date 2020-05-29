import pytest

from matcha.fsm import MatchaState, DoubleMatchaState, Card

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


@pytest.fixture
def matchastate():
    s = MatchaState({
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


def test_from_data():
    data = {
        'players': [{
            'name': 'piestastedgood',
            'hand': [
                {'suit': 3, 'rank': 3}
            ]

        }, {
            'name': 'tripswithtires',
            'hand': [
                {'suit': 1, 'rank': 11}
            ]
        }],
        'state': {
            'player': 'tripswithtires',
            'state': 'foreplace',
            'game_id': 0
        }
    }
    state = DoubleMatchaState.from_data(data)

    assert(len(state.players) == 2)
    assert(state.state.player.name == 'tripswithtires')
    assert(state.state.state_name == data['state']['state'])
    assert(state.state.game_id == data['state']['game_id'])

    assert(len(state.players[0].hand) == len(data['players'][0]['hand']))
    assert(type(state.players[0].hand[0]) == Card)


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
    hand = state.next_player().hand

    state.lead(lead_card.to_data())

    assert(state.valid_follow(lead_card, follow_card, hand) == True)


def test_valid_follow_rank(state: DoubleMatchaState):
    lead_card = Card(Card.Suit.CLUBS, Card.Rank.KING)
    follow_card = Card(Card.Suit.HEARTS, Card.Rank.KING)

    state.current_player().hand = [lead_card]
    state.next_player().hand = [follow_card]
    hand = state.next_player().hand

    state.lead(lead_card.to_data())

    assert(state.valid_follow(lead_card, follow_card, hand) == True)


def test_valid_follow_rank_but_suit(state: DoubleMatchaState):
    lead_card = Card(Card.Suit.CLUBS, Card.Rank.KING)
    follow_card = Card(Card.Suit.HEARTS, Card.Rank.KING)

    state.current_player().hand = [lead_card]
    state.next_player().hand = [follow_card, Card(Card.Suit.CLUBS, Card.Rank.SEVEN)]
    hand = state.next_player().hand

    state.lead(lead_card.to_data())

    assert(state.valid_follow(lead_card, follow_card, hand) == False)


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


def test_foreplace(matchastate: MatchaState):
    foreplace_card = matchastate.current_player().hand[0]
    matchastate.foreplace(foreplace_card.to_data())

    assert(matchastate.state.state_name == 'foreplace')
    assert(matchastate.state.player == matchastate.players[1])

    assert(foreplace_card not in matchastate.players[0].hand)
    assert(foreplace_card in matchastate.players[0].foreplace)

    second_card = matchastate.current_player().hand[0]
    matchastate.foreplace(second_card.to_data())

    assert(matchastate.state.state_name == 'lead')
    assert(matchastate.state.player == matchastate.players[0])

    assert(second_card not in matchastate.players[1].hand)
    assert(second_card in matchastate.players[1].foreplace)


def test_end_game(state: DoubleMatchaState):
    lead_card = Card(Card.Suit.CLUBS, Card.Rank.KING)
    follow_card = Card(Card.Suit.HEARTS, Card.Rank.KING)

    second_player = state.next_player()

    state.current_player().hand = [lead_card]
    state.next_player().hand = [follow_card]

    state.lead(lead_card.to_data())
    state.follow(follow_card.to_data())

    assert(state.state.state_name == 'foreplace')
    assert(state.current_player() == second_player)
    assert(state.current_player().hand == [lead_card])
    assert(state.next_player().hand == [follow_card])
    assert(len(state.current_player().tableau) == 0)
    assert(len(state.current_player().foreplace) == 0)

    state.skip_foreplace()

    assert(state.state.state_name == 'foreplace')


def test_end_second_game(state: DoubleMatchaState):
    lead_card = Card(Card.Suit.CLUBS, Card.Rank.KING)
    follow_card = Card(Card.Suit.HEARTS, Card.Rank.KING)

    second_player = state.next_player()
    state.state.game_id = 1

    state.current_player().hand = [lead_card]
    state.next_player().hand = [follow_card]

    state.lead(lead_card.to_data())
    state.follow(follow_card.to_data())

    assert(state.state.state_name == "foreplace")


def test_to_data_twice(state: DoubleMatchaState):
    state.to_data()
    state.to_data()


def test_skip_foreplace(state: DoubleMatchaState):
    state.skip_foreplace()

    assert(len(state.players[0].foreplace) == 0)
    assert(state.state.state_name == 'foreplace')
    assert(state.state.player == state.players[1])


def test_second_foreplace_bug():
    data = {
      "players": [
        {
          "name": "admin",
          "hand": [
            {"suit": 4, "rank": 11 },
            {"suit": 2, "rank": 10 },
            {"suit": 3, "rank": 10 },
            {"suit": 1, "rank": 11 },
            {"suit": 3, "rank": 3 },
            {"suit": 3, "rank": 4 },
            {"suit": 2, "rank": 7 },
            {"suit": 3, "rank": 11 },
            {"suit": 3, "rank": 7 }
          ],
          "tableau": [],
          "foreplace": [
            {"suit": 1, "rank": 4 }
          ]
        },
        {
          "name": "foobar",
          "hand": [
            {"suit": 4, "rank": 10 },
            {"suit": 4, "rank": 7 },
            {"suit": 2, "rank": 3 },
            {"suit": 2, "rank": 11 },
            {"suit": 1, "rank": 3 },
            {"suit": 1, "rank": 10 },
            {"suit": 2, "rank": 4 },
            {"suit": 4, "rank": 4 },
            {"suit": 1, "rank": 7 },
            {"suit": 4, "rank": 3 }
          ],
          "tableau": [],
          "foreplace": []
        }
      ],
      "state": {
        "player": "foobar",
        "state": "foreplace",
        "game_id": 0
      }
    }

    state = MatchaState.from_data(data)
    for p in state.players:
        print(f"very beginning {p.name} foreplace = {p.foreplace}")

    state.foreplace({"suit": 4, "rank": 10})
    print(f"after foreplace call {state.players[1].foreplace}")

    assert(len(state.players[1].foreplace) == 1)

    print(f"before to_data call {state.players[1].foreplace}")
    for p in state.players:
        print(f"before to_data {p.name} foreplace = {p.foreplace}")

    new_data = state.to_data()

    assert(len(new_data['players'][1]['foreplace']) == 1)


def test_buggy_follow():
    data = {
      "players": [
        {
          "name": "admin",
          "hand": [
            {"suit": 4, "rank": 11 },
            {"suit": 3, "rank": 10 },
            {"suit": 1, "rank": 11 },
            {"suit": 3, "rank": 3 },
            {"suit": 3, "rank": 4 },
            {"suit": 2, "rank": 7 },
            {"suit": 3, "rank": 11 },
            {"suit": 3, "rank": 7 }
          ],
          "tableau": [
            {"suit": 2, "rank": 10 }
          ],
          "foreplace": [
            {"suit": 1, "rank": 4 }
          ]
        },
        {
          "name": "foobar",
          "hand": [
            {"suit": 4, "rank": 10 },
            {"suit": 4, "rank": 7 },
            {"suit": 2, "rank": 3 },
            {"suit": 2, "rank": 11 },
            {"suit": 1, "rank": 3 },
            {"suit": 1, "rank": 10 },
            {"suit": 2, "rank": 4 },
            {"suit": 4, "rank": 4 },
            {"suit": 1, "rank": 7 },
            {"suit": 4, "rank": 3 }
          ],
          "tableau": [],
          "foreplace": []
        }
      ],
      "state": {
        "player": "foobar",
        "state": "follow",
        "game_id": 0
      }
    }

    state = MatchaState.from_data(data)
    state.follow({"suit": Card.Suit.SPADES.value, "rank": Card.Rank.ACE.value})

    assert(state.state.state_name == 'lead')
    assert(state.state.player.name == 'foobar')

    new_data = state.to_data()
    assert(new_data['state']['state'] == 'lead')
    assert(new_data['state']['player'] == 'foobar')


def test_matcha(matchastate: MatchaState):
    lead_card = Card(Card.Suit.CLUBS, Card.Rank.KING)
    follow_card = Card(Card.Suit.HEARTS, Card.Rank.SEVEN)

    second_player = matchastate.next_player()

    matchastate.current_player().hand = [lead_card]
    matchastate.next_player().hand = [follow_card]

    matchastate.lead(lead_card.to_data())

    assert(matchastate.state.state_name == 'matcha')
    assert(matchastate.current_player().score == 4)


def test_no_a_matcha():
    state = MatchaState.from_data({
      "players": [
        {
          "name": "admin",
          "hand": [
            {"suit": 3, "rank": 10 },
            {"suit": 3, "rank": 3 },
            {"suit": 3, "rank": 11 }
          ],
          "tableau": [
            {"suit": 2, "rank": 10 },
            {"suit": 4, "rank": 11 },
            {"suit": 3, "rank": 7 },
            {"suit": 1, "rank": 11 },
            {"suit": 3, "rank": 4 },
            {"suit": 2, "rank": 7 }
          ],
          "foreplace": [
            {"suit": 1, "rank": 4 }
          ],
          "score": 0,
          "ready": False
        },
        {
          "name": "foobar",
          "hand": [
            {"suit": 4, "rank": 7 },
            {"suit": 1, "rank": 10 },
            {"suit": 4, "rank": 4 },
            {"suit": 4, "rank": 3 }
          ],
          "tableau": [
            {"suit": 2, "rank": 11 },
            {"suit": 4, "rank": 10 },
            {"suit": 1, "rank": 7 },
            {"suit": 1, "rank": 3 },
            {"suit": 2, "rank": 4 },
            {"suit": 2, "rank": 3 }
          ],
          "foreplace": [],
          "score": 0,
          "ready": False
        }
      ],
      "state": {
        "player": "foobar",
        "state": "lead",
        "game_id": 0
      }
    })

    state.lead(Card(
        Card.Suit.DIAMONDS, Card.Rank.QUEEN
    ).to_data())

    assert(state.state.state_name == 'follow')

def test_overmatch(matchastate: MatchaState):
    foreplace_card = Card(Card.Suit.HEARTS, Card.Rank.KING)
    lead_card = Card(Card.Suit.CLUBS, Card.Rank.KING)
    follow_card = Card(Card.Suit.CLUBS, Card.Rank.SEVEN)
    follow_card2 = Card(Card.Suit.CLUBS, Card.Rank.QUEEN)

    second_player = matchastate.next_player()

    matchastate.current_player().hand = [foreplace_card, lead_card]
    matchastate.next_player().hand = [follow_card, follow_card2]

    matchastate.foreplace(foreplace_card.to_data())
    matchastate.skip_foreplace()
    matchastate.lead(lead_card.to_data())
    matchastate.follow(follow_card.to_data())

    assert(matchastate.state.state_name == 'follow')
    assert(matchastate.next_player().last_played() == Card(Card.Suit.CLUBS, Card.Rank.KING))
