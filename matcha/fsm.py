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
        self.foreplace = data['foreplace'] if 'foreplace' in data else []
        self.score = data['score'] if 'score' in data else 0
        self.turn_order = turn_order
        self.ready = data['ready'] if 'ready' in data else False
        self.foreplaced = data['foreplaced'] if 'foreplaced' in data else False

    def set_hand(self, hand):
        self.hand = hand

    def play_foreplace(self, card):
        if card not in self.hand:
            raise CardNotInHand(card)

        self.hand.remove(card)
        self.foreplace.append(card)
        self.foreplaced = True

    def play_card(self, card):
        if card in self.hand:
            # raise CardNotInHand(card)
            self.hand.remove(card)

        self.tableau.append(card)

    def last_played(self):
        return self.tableau[-1]

    def increase_score(self, new_score):
        self.score += new_score

    def to_data(self):
        hand = [c.to_data() for c in self.hand]
        tableau = [c.to_data() for c in self.tableau]
        foreplace = [c.to_data() for c in self.foreplace]
        return {
            'name': self.name,
            'hand': hand,
            'tableau': tableau,
            'foreplace': foreplace,
            'score': self.score,
            'ready': self.ready,
            'foreplaced': self.foreplaced
        }

    def __repr__(self):
        return f'{self.name}: {self.hand}'

    def __str__(self):
        return self.__repr__()


class State:
    def __init__(self, player, state_name, game_id=0):
        self.player = player
        self.state_name = state_name
        self.game_id = game_id

    @staticmethod
    def from_data(data):
        return State(data['player'], data['state'], data['game_id'])

    def to_data(self):
        return {
            "player": self.player.name,
            "state": self.state_name,
            "game_id": self.game_id,
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
        if type(self.deck[0]) != Card:
            self.deck = [Card(s, r) for s, r in self.deck]
        random.shuffle(self.deck)

        self.players[0].set_hand(self.deck[:10])
        self.players[1].set_hand(self.deck[10:])

        self.state = State(self.players[0], self.initial_state)

    def lead(self, card_data):
        card = Card.from_data(card_data)
        self.current_player().play_card(card)

        valid_plays = [
            c for c in self.next_player().hand if self.valid_follow(
                lead_card=card,
                follow_card=c,
                hand=self.next_player().hand
            )
        ]
        if len(valid_plays) == 0:
            self.transition('matcha')
        else:
            self.transition('follow', next_player=True)

    def follow(self, card_data):
        card = Card.from_data(card_data)

        if self.valid_follow(
            lead_card=self.next_player().last_played(),
            follow_card=card,
            hand=self.current_player().hand
        ):
            self.current_player().play_card(card)
        else:
            raise CardNotPlayable(card)

        # TODO transition to "draw" game end if no cards left in other player's hand
        # If next_player's hand is empty
        if not self.next_player().hand:
            # this is a draw, no score?
            if len(self.next_player().foreplace) == 1:
                self.transition('lead', next_player=True)
                self.lead(self.current_player().last_played().to_data())
            else:
                print("It's a draw")
                self.end_game()
        else:
            self.transition(
                'lead',
                next_player=self.current_player().last_played() <= self.next_player().last_played()
            )

    def foreplace_transition(self):
        return 'foreplace' if not self.next_player().foreplaced else 'lead'

    def skip_foreplace(self, _=None):
        self.current_player().foreplaced = True
        next_state = self.foreplace_transition()
        self.transition(next_state, next_player=True)

    def foreplace(self, card_data):
        card = Card.from_data(card_data)
        self.current_player().play_foreplace(card)

        next_state = self.foreplace_transition()
        self.transition(next_state, next_player=True)

    def valid_follow(self, lead_card, follow_card, hand):
        # follow is valid if it matches suit, or if it matches number and there are no suit matches
        return (
            follow_card.suit == lead_card.suit or 
            not any([
                c.suit == lead_card.suit for c in hand]
            ) and follow_card.rank == lead_card.rank
        )

    def end_game(self):
        next_state = self.initial_state

        first_hand = self.players[0].hand + self.players[0].foreplace + self.players[0].tableau
        second_hand = self.players[1].hand + self.players[1].foreplace + self.players[1].tableau

        self.players[0].hand = second_hand
        self.players[1].hand = first_hand

        for player in self.players:
            player.tableau = []
            player.foreplace = []
            player.foreplaced = False
            player.ready = False

        self.state.game_id += 1

        if self.state.game_id % 2 == 0:
            self.initialize()
        self.transition(next_state, player=self.players[1])

    def declare_matcha(self):
        """Called when state.player cannot follow lead."""
        pass

    def current_player(self):
        return self.state.player

    def next_player(self):
        return self.players[(self.state.player.turn_order + 1) % len(self.players)]

    def compute_score(self):
        winner = self.current_player()
        winner.increase_score(len(winner.tableau) * winner.last_played().rank.value)

    def next_game(self, player_name):
        player = [p for p in self.players if p.name == player_name][0]
        player.ready = True

        if all([p.ready for p in self.players]):
            self.end_game()

    def transition(self, state, next_player=False, player=None):
        if next_player:
            self.state.set_player(self.next_player())

        if player is not None:
            self.state.set_player(player)

        if state == 'matcha':
            self.compute_score()

        self.state.set_state_name(state)

    @staticmethod
    def from_data(data):
        for player in data['players']:
            player['hand'] = [Card.from_data(c) for c in player['hand']]
            player['tableau'] = [Card.from_data(c) for c in player['tableau']] if 'tableau' in player else []
            player['foreplace'] = [Card.from_data(c) for c in player['foreplace']] if 'foreplace' in player else []
        state = MatchaState(data)
        data['state']['player'] = [p for p in state.players if p.name == data['state']['player']][0]
        state.state = State.from_data(data['state'])
        return state

    def to_data(self):
        return {
            'players': [p.to_data() for p in self.players],
            'state': self.state.to_data()
        }


class DoubleMatchaState(BaseMatchaGame):
    initial_state = 'foreplace'

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
    initial_state = 'foreplace'

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

