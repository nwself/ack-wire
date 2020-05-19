from transitions import Machine, State
from .fsm import Card

class BaseMatchaGame:
    states = [
        State(
            name='uninitialized',
            on_exit=["build_game"]
        ),
        'foreplace',
        'lead',
        'follow'
    ]

    def __init__(self):
        self.machine = Machine(model=self, states=MatchaGame.states, initial='uninitialized')

        self.machine.add_transition(
            trigger='initialize',
            source='uninitialized',
            dest='foreplace',
        )

    def build_game(self):
        self.deck = [Card(s, r) for s, r in self.deck]


class MatchaGame(BaseMatchaGame):
    deck = [
        (Card.Suit.CLUBS, Card.Rank.ACE),
        (Card.Suit.CLUBS, Card.Rank.TEN),
        (Card.Suit.CLUBS, Card.Rank.KING),
        (Card.Suit.CLUBS, Card.Rank.QUEEN),
        (Card.Suit.CLUBS, Card.Rank.SEVEN),

        (Card.Suit.SPADES, Card.Rank.ACE),
        (Card.Suit.SPADES, Card.Rank.TEN),
        (Card.Suit.SPADES, Card.Rank.KING),
        (Card.Suit.SPADES, Card.Rank.QUEEN),
        (Card.Suit.SPADES, Card.Rank.SEVEN),

        (Card.Suit.HEARTS, Card.Rank.ACE),
        (Card.Suit.HEARTS, Card.Rank.TEN),
        (Card.Suit.HEARTS, Card.Rank.KING),
        (Card.Suit.HEARTS, Card.Rank.QUEEN),
        (Card.Suit.HEARTS, Card.Rank.SEVEN),

        (Card.Suit.DIAMONDS, Card.Rank.ACE),
        (Card.Suit.DIAMONDS, Card.Rank.TEN),
        (Card.Suit.DIAMONDS, Card.Rank.KING),
        (Card.Suit.DIAMONDS, Card.Rank.QUEEN),
        (Card.Suit.DIAMONDS, Card.Rank.SEVEN),
    ]
