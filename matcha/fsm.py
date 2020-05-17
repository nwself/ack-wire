from enum import Enum
from functools import total_ordering
import random


# create game
#   make players
#   make game
#   make first game state
#   state = {...}
#   first player takes turn
#   get state from db
#   initialize one of these
#   validate move
#   return new state

@total_ordering
class Card:
    class Suit(Enum):
        CLUBS = 1
        SPADES = 2
        HEARTS = 3
        DIAMONDS = 4

    class Rank(Enum):
        ACE = 11
        TEN = 10
        KING = 4
        QUEEN = 3
        SEVEN = 7

    suit_str = {
        Suit.CLUBS: "♣",
        Suit.SPADES: "♠",
        Suit.HEARTS: "♥",
        Suit.DIAMONDS: "♦",
    }

    rank_str = {
        Rank.ACE: "A",
        Rank.TEN: "10",
        Rank.KING: "K",
        Rank.QUEEN: "Q",
        Rank.SEVEN: "7",
    }

    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank

    def to_data(self):
        return {
            "suit": self.suit.value,
            "rank": self.rank.value
        }

    @staticmethod
    def from_data(card_data):
        return Card(Card.Suit(card_data['suit']), Card.Rank(card_data['rank']))

    def __lt__(self, other):
        # return whether self is less than other
        return (
            other.suit.value < self.suit.value or
            other.suit == self.suit and (
                (self.rank.value if self.rank != Card.Rank.SEVEN else 1) < 
                (other.rank.value if other.rank != Card.Rank.SEVEN else 1)
            )
        )

    def __eq__(self, other):
        return self.suit == other.suit and self.rank == other.rank

    def __str__(self):
        return f'{self.suit_str[self.suit]}{self.rank_str[self.rank]}'

    def __repr__(self):
        return self.__str__()


class Player:
    def __init__(self, data, turn_order):
        self.name = data['name']
        self.hand = data['hand'] if 'hand' in data else []
        self.tableau = data['tableau'] if 'tableau' in data else []
        # self.foreplace = data['foreplace'] if 'foreplace' in data else []
        self.turn_order = turn_order

    def set_hand(self, hand):
        self.hand = hand

    # def play_foreplace(self, card):
    #     self._play_card(card, 'foreplace')

    def play_card(self, card):
        self._play_card(card, 'hand')

    def play_card(self, card):
        if card not in self.hand:
            raise CardNotInHand(card)

        self.hand.remove(card)
        self.tableau.append(card)

    def last_played(self):
        return self.tableau[-1]

    def to_data(self):
        return {
            'name': self.name,
            'hand': [c.to_data() for c in self.hand],
            'tableau': [c.to_data() for c in self.tableau],
            # 'foreplace': [c.to_data() for c in self.foreplace],
        }

    def __repr__(self):
        return f'{self.name}: {self.hand}'

    def __str__(self):
        return self.__repr__()


class State:
    def __init__(self, player, state_name):
        self.player = player
        self.state_name = state_name

    def to_data(self):
        return {
            "player": self.player.name,
            "state": self.state_name
        }

    def set_player(self, player):
        self.player = player

    def set_state_name(self, name):
        self.state_name = name

    def __repr__(self):
        return f'{self.player.name}: {self.state_name}'

    def __str__(self):
        return self.__repr__()


class BaseMatchaGame:
    def __init__(self, data):
        self.players = [Player(p, i) for i, p in enumerate(data['players'])]

    def initialize(self):
        self.deck = [Card(s, r) for s, r in self.deck]
        random.shuffle(self.deck)

        self.players[0].set_hand(self.deck[:10])
        self.players[1].set_hand(self.deck[10:])

        self.state = State(self.players[0], 'lead')

    def lead(self, card_data):
        card = Card.from_data(card_data)
        self.current_player().play_card(card)
        self.transition('follow', next_player=True)

    def follow(self, card_data):
        card = Card.from_data(card_data)

        if self.valid_follow(card):
            self.current_player().play_card(card)
        else:
            raise CardNotPlayable(card)

        # TODO transition to "draw" game end if no cards left in other player's hand
        self.transition(
            'lead',
            next_player=self.current_player().last_played() <= self.next_player().last_played()
        )

    # def foreplace(self, card_data):
    #     card = Card.from_data(card_data)
    #     self.current_player().play_foreplace(card)

    def valid_follow(self, card):
        # follow is valid if it matches suit, or if it matches number and there are no suit matches
        lead_card = self.next_player().last_played()
        return (
            card.suit == lead_card.suit or 
            not any([c.suit == lead_card.suit for c in self.current_player().hand]) and card.rank == lead_card.rank
        )

    def declare_matcha(self):
        """Called when state.player cannot follow lead."""
        pass

    def current_player(self):
        return self.state.player

    def next_player(self):
        return self.players[(self.state.player.turn_order + 1) % len(self.players)]

    def transition(self, state, next_player=False):
        if next_player:
            self.state.set_player(self.next_player())
        self.state.set_state_name(state)

    def to_data(self):
        return {
            'players': [p.to_data() for p in self.players],
            'state': self.state.to_data()
        }


class DoubleMatchaState(BaseMatchaGame):
    deck = [
        (Card.Suit.CLUBS, Card.Rank.ACE),
        (Card.Suit.CLUBS, Card.Rank.TEN),
        (Card.Suit.CLUBS, Card.Rank.KING),
        (Card.Suit.CLUBS, Card.Rank.SEVEN),
        (Card.Suit.CLUBS, Card.Rank.SEVEN),

        (Card.Suit.SPADES, Card.Rank.ACE),
        (Card.Suit.SPADES, Card.Rank.TEN),
        (Card.Suit.SPADES, Card.Rank.KING),
        (Card.Suit.SPADES, Card.Rank.KING),
        (Card.Suit.SPADES, Card.Rank.SEVEN),

        (Card.Suit.HEARTS, Card.Rank.ACE),
        (Card.Suit.HEARTS, Card.Rank.TEN),
        (Card.Suit.HEARTS, Card.Rank.TEN),
        (Card.Suit.HEARTS, Card.Rank.KING),
        (Card.Suit.HEARTS, Card.Rank.SEVEN),

        (Card.Suit.DIAMONDS, Card.Rank.ACE),
        (Card.Suit.DIAMONDS, Card.Rank.ACE),
        (Card.Suit.DIAMONDS, Card.Rank.TEN),
        (Card.Suit.DIAMONDS, Card.Rank.KING),
        (Card.Suit.DIAMONDS, Card.Rank.SEVEN),
    ]


class MatchaState(BaseMatchaGame):
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


class TutorialGame(BaseMatchaGame):
    initial_state = 'lead'


class StandardGame(BaseMatchaGame):
    initial_state = 'foreplace'

