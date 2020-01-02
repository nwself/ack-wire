import abc
import json
import math
import logging
import random

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
# from django.core.exceptions import PermissionDenied
# from django.http import HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404
from django.utils.safestring import mark_safe


from .models import Game, GameState, build_initial_state


logger = logging.getLogger(__file__)


@login_required
def lobby(request):
    return render(request, 'games/lobby.html', {
        'current_games': request.user.game_set.all()
    })


@login_required
def game(request, game_pk):
    game = get_object_or_404(Game, pk=game_pk)
    state = game.get_active_state()

    for player in state['players']:
        if player['username'] != request.user.username:
            del player['tiles']
    del state['supply']['tiles']

    return render(request, 'games/game.html', {
        'game_name_json': mark_safe(json.dumps(game_pk)),
        'game_state_json': mark_safe(json.dumps(state))
    })

# A whole game will be stored as a state in a JSON object
# Views will look up a game by id and mutate state in the requested way after checking that it's legit

# class based?

# Does client or server prompt for the next action??? or maybe there's a "state" key on the
#   state object that identifies who needs to do what next?

# tile      ->             stocks -> draw -> (back to tile with next player)
#      -> merger        ->
#                       -> (back to merger)
#      -> declare_chain ->

# merger
# determine_winners -> dispose_stock,pc -> dispose_stock,pc+1 -> ... -> (back to dispose_stock,pc with next chain or) -> stocks

# state = {
#     chains = [
#         "luxor": 2        # count of hotels in this chain
#         "continental": 0  # this means this chain is available to play
#     ],
#     rows = [
#         [
#             Cell("A1", None),
#             Cell("A2", "luxor"),  # string must match "chains" keys
#             Cell("A3", "luxor"),
#             Cell("B7", "island")  # "island" for hotels that aren't a chain yet
#         ]
#     ]
#     players = [       # clients shouldn't have all of this
#        "phil": {      # these players should be in turn order
#            "cash": 100,
#            "stocks": {
#                "luxor": 3,
#            },
#            "tiles": [
#                "A4",
#            ]
#        }
#     ]
#     supply = {      # clients shouldn't have this
#        "stocks": [
#            "luxor": 22
#        ],
#        "tiles": ["A5", "A6", ...]
#     }
#     merging_chains: [   # only on state if a merge is active
#        "imperial",  # winner is first
#        "worldwide", # second loser
#        "american"   # first loser, even if tied with worldwide
#     ]
#     defunct_chains: [   # needed to resolve merger since merging_chains will be mutated
#        "worldwide",
#        "american"
#     ]
#     merging_player: "player_id"
#     active_cell: "D5",  # used for recently placed tile
#     game: "game_id"
#     state: {
#        "player": "player_id",
#        "state": "play_tile"    # this is state.state.state which is a stupid thing to call something
#     }
#     end_game: False     # used to end game when a player calls it
# }


def start_game(game_slug, usernames):
    """Create a new game.

    Takes a list of players to put in this game.

    Create the initial state and save to Game model, whatever that might be.

    Copy an initial state JSON.
    Draw a tile for each player, place on board with chain = "island"
    Order players by the number drawn.
    Draw 6 tiles for each player.

    Save this initial state to the model.
    Notify all.
    """
    users = []
    for username in usernames:
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            logger.error("User does not exist {}".format(username))
            return None
        users.append(user)

    state = build_initial_state(users)

    # Draw a tile for each player
    initial_draws = [(player, draw_tile(state)) for player in state['players']]
    initial_draws.sort(key=lambda x: x[1])

    # Order players by the tiles drawn
    state['players'] = [x[0] for x in initial_draws]
    state['state']['player'] = state['players'][0]['username']

    state['history'].append([
        'initial_draws',
        [[x[0]['username'], x[1]] for x in initial_draws]
    ])

    # Place initial draws on board with chain = "island"
    for draw in initial_draws:
        state['hotels'][draw[1]] = 'island'

    # Draw 6 tiles for each player
    for player in state['players']:
        player['tiles'] = [draw_tile(state) for _ in range(6)]

    # Save game to database
    game = Game.objects.create(name=game_slug)
    for user in users:
        game.users.add(user)
    game.save()

    # Save initial state to database
    GameState.objects.create(game=game, state=json.dumps(state))
    return state


def notify_all(state):
    """Send the new state to everyone.

    Each player needs a subset of the total state so they don't get each other tiles.

    Send whole state except remove supply.tiles and player.tiles for everyone but recipient.
    """
    pass


class ActionForbiddenException(Exception):
    def __init__(self, text=''):
        super(Exception, self).__init__()
        self.text = text


class Action(abc.ABC):
    def __init__(self, game_pk, user):
        super(Action, self).__init__()

        self.game_pk = game_pk
        self.user = user

        game_query = user.game_set.filter(pk=game_pk)
        if not game_query.exists():
            logger.error("{} not in game {}".format(user.username, game_pk))
            print("{} not in game {}".format(user.username, game_pk))
            raise ActionForbiddenException()

        self.game = game_query[0]  # must be only one because pk is unique
        self.state = self.game.get_active_state()

        if self.state['state']['state'] == 'end_game':
            logger.error('{} sent a play but game is over'.format(user.username))
            raise ActionForbiddenException()

    @abc.abstractmethod
    def process(self):
        pass


class TurnAction(Action):
    def __init__(self, game_pk, user):
        super(TurnAction, self).__init__(game_pk, user)

        if self.state['state']['player'] != user.username:
            print('{} sent a play but it is not their turn'.format(user.username))
            logger.error('{} sent a play but it is not their turn'.format(user.username))
            raise ActionForbiddenException()

        # Get current player (safe because user must be in players since they are in this game)
        # (unless coding error)
        self.player = pluck_player(self.state, user.username)

    # def advance_to_dispose_stock(self):
    #     return state['state']['state'] = 'dispose_stock'

    def advance_to_next_dispose_stock(self):
        # called by prepare_merger after pay_bonuses
        # and recursively after pay_bonuses for queued merger
        defunct_chain = self.state['merging_chains'][-1]

        # find the next player with shares of defunct_chain or stop at merging_player
        n_player = next_player(self.state)
        self.state['state']['player'] = n_player

        while (pluck_player(self.state, n_player)['stocks'][defunct_chain] == 0 and
                n_player != self.state['merging_player']):
            n_player = next_player(self.state)
            self.state['state']['player'] = n_player

        # after while loop, state.state.player will be either
        #   the next player with shares of defunct_chain
        #   merging_player which means we are done with *this* merger
        if n_player == self.state['merging_player']:
            # if everyone has had a chance to dispose stock
            # remove the current loser from merging_chains
            self.state['merging_chains'] = self.state['merging_chains'][:-1]
            if len(self.state['merging_chains']) > 1:
                # If there is another merger to resolve
                pay_bonuses(self.state)
                if pluck_player(self.state, n_player)['stocks'][self.state['merging_chains'][-1]] > 0:
                    self.state['state']['state'] = 'dispose_stock'
                else:
                    self.advance_to_next_dispose_stock()
            else:
                # all merging is done
                resolve_merge(self.state)
                self.player = pluck_player(self.state, self.state['merging_player'])
                self.advance_to_buy_or_next()
        else:
            # another player needs to dispose stock of loser
            self.state['state']['state'] = 'dispose_stock'

    def advance_to_buy_or_next(self):
        if (any([c for c in self.state['chains'] if self.state['chains'][c] > 0]) and
                min([get_stock_cost(self.state, c) for c in self.state['chains']]) <= self.player['cash']):
            # If there are any active chains and player has enough cash go to buy_stocks state
            self.state['state']['state'] = 'buy_stocks'
        else:
            if self.state['end_game']:
                self.end_game()
                return self.state
            else:
                # There are no active chains so draw a tile and it's next player's turn
                self.player['tiles'].append(draw_tile(self.state))
                self.state['state'] = {
                    'state': 'play_tile',
                    'player': next_player(self.state)
                }

    def prepare_merger(self, state):
        """Modify state to start mergering.

        Set merging_chains on state to match requested order
        Set defunct_chains to merging_chains[1:]

        Call pay_bonuses (should pay for first merger)
        Set state to "dispose_loser,current_player"
        """
        state['defunct_chains'] = state['merging_chains'][1:]
        state['merging_player'] = state['state']['player']

        state['history'].append([
            'prepare_merger',
            state['merging_player'],
            [[c, state['chains'][c]] for c in state['merging_chains']]
        ])

        pay_bonuses(state)
        if pluck_player(state, state['state']['player'])['stocks'][state['merging_chains'][-1]] > 0:
            state['state']['state'] = 'dispose_stock'
        else:
            self.advance_to_next_dispose_stock()

    def end_game(self):
        # Payout final bonuses
        # Convert shares to cash
        # Add up cash
        active_chains = [c for c in self.state['chains'] if self.state['chains'][c] > 0]
        for chain in active_chains:
            self.state['merging_chains'] = [chain]
            pay_bonuses(self.state)

        for chain in active_chains:
            for player in self.state['players']:
                income = player['stocks'][chain] * get_stock_cost(self.state, chain)
                player['cash'] += income
                self.state['history'].append(['sell_stocks', player['username'], player['stocks'][chain], chain, income])

        self.state['state']['state'] = 'end_game'
        self.state['state']['player'] = ''

        GameState.objects.create(game=self.game, state=json.dumps(self.state))


class PlayTileAction(TurnAction):
    def __init__(self, game_pk, user, tile):
        super(PlayTileAction, self).__init__(game_pk, user)
        self.tile = tile

    def start_merger_helper(self, state, merging_chains):
        """Check if winner chain can be auto-declared for a new merger.

        Called from play_tile if a merger has happened. Uses "active_cell" on state.

        Assuming that merger is valid and there are not two safe chains involved.

        Determine merging chains
            Find chains of orthogonally adjacent cells

        Add "merging_chains" to state from highest to lowest size
        First in list will be winner and last will be smallest/first loser

        If any two chains have the same size
            Set state to "determine_winner_chain"
            Client can prompt using "merging_chains" on state
        Else:
            Call prepare_merger
        """
        neighbors = set([c for c in get_neighboring_assignments(state, state['active_cell']) if c is not None and c != "island"])
        state['merging_chains'] = sorted(list(neighbors), key=lambda x: state['chains'][x], reverse=True)

        chain_sizes = [state['chains'][c] for c in state['merging_chains']]
        if len(set(chain_sizes)) != len(chain_sizes):
            # One or more chains have the same size
            state['state']['state'] = 'determine_winner'
        else:
            self.prepare_merger(state)

    def process(self):
        state = self.state
        player = self.player

        if self.tile not in player['tiles']:
            logger.error("{} trying to play tile {} not in hand".format(player['username'], self.tile))
            raise ActionForbiddenException()

        # Set active_cell
        state['active_cell'] = self.tile
        neighbors = get_neighboring_assignments(state, self.tile)

        # Remove played tile from hand
        player['tiles'].remove(self.tile)

        history_added = False
        if all([n is None for n in neighbors]):
            # if no neigboring hotels
            state['hotels'][self.tile] = 'island'
            self.advance_to_buy_or_next()
        elif all([n is None or n == 'island' for n in neighbors]):
            # if there are only island hotels adjacent
            if any([c for c in state['chains'] if state['chains'][c] == 0]):
                # If there are available chains in the supply
                state['hotels'][self.tile] = 'island'
                state['state']['state'] = 'declare_chain'
            else:
                # TODO client need to prevent user from forming chains with no chains available
                logger.error("{} plays {} to form chain but no available chains".format(player['username'], self.tile))
                raise ActionForbiddenException("No available chains")
        else:
            # There must at least be one chain adjacent
            neighboring_chains = set([n for n in neighbors if n is not None and n != 'island'])
            if len(neighboring_chains) == 1:
                # If all have chain == None or chain == island or chain == some_chain:
                size = 1
                chain = neighboring_chains.pop()
                state['hotels'][self.tile] = chain
                if 'island' in neighbors:
                    size += convert_islands(state, chain)
                state['chains'][chain] += size
                self.advance_to_buy_or_next()
            else:
                # Check if this tile is unplayable (should probably be a helper function)
                safe_neighbors = [n for n in neighboring_chains if state['chains'][n] >= 11]
                if len(safe_neighbors) >= 2:
                    # just draw a new tile
                    state['history'].append(['discard_unplayable_tile', self.tile])
                    history_added = True
                    self.player['tiles'].append(draw_tile(self.state))
                    # logger.error("Cannot play {} because 2+ neighboring chains are safe".format(self.tile))
                    # raise ActionForbiddenException()
                else:
                    state['history'].append([
                        'play_tile',
                        player['username'],
                        self.tile,
                        'merger'
                    ])
                    history_added = True

                    # Set current cell to island while merger is going on
                    state['hotels'][state['active_cell']] = 'island'
                    # Change state to merger
                    self.start_merger_helper(state, neighboring_chains)

        if not history_added:
            state['history'].append([
                'play_tile',
                player['username'],
                self.tile,
                self.state['hotels'][self.tile]
            ])

        GameState.objects.create(game=self.game, state=json.dumps(state))
        return state


class DeclareChainAction(TurnAction):
    def __init__(self, game_pk, user, chain):
        super(DeclareChainAction, self).__init__(game_pk, user)
        self.chain = chain

    def process(self):
        #     Is chain available?
        if self.chain not in [c for c in self.state['chains'] if self.state['chains'][c] == 0]:
            logger.error("{} tried to found already active chain {}".format(self.player['username'], self.chain))
            raise ActionForbiddenException()

        # If it checks out:
        #     Use active_cell from state, set its chain to "chain"
        self.state['hotels'][self.state['active_cell']] = self.chain

        # Track size of new chain as we go
        size = 1

        #     Do a crazy search through the board to set all orthogonally adjacent "island" cells to "chain"
        size += convert_islands(self.state, self.chain)

        # Set size of chain
        self.state['chains'][self.chain] = size

        #     Add one stock of declared chain to player's hand
        self.player['stocks'][self.chain] += 1

        #     Subtract one stock from supply
        self.state['supply']['stocks'][self.chain] -= 1

        self.state['history'].append([
            'declare_chain',
            self.player['username'],
            self.chain
        ])

        # Set state to "buy_stocks" and notify all.
        # self.state['state']['state'] = 'buy_stocks'
        self.advance_to_buy_or_next()

        GameState.objects.create(game=self.game, state=json.dumps(self.state))
        return self.state


class BuyStocksAction(TurnAction):
    def __init__(self, game_pk, user, stocks):
        super(BuyStocksAction, self).__init__(game_pk, user)
        self.stocks = stocks

    def process(self):
        #     Has this player asked for more than 3 stocks?
        if len(self.stocks) > 3:
            logger.error("{} buys more than 3 stocks {}".format(self.user, self.stocks))
            raise ActionForbiddenException("Buying more than 3 stocks")
        #     Are these stocks available in the supply?

        #     Does this player have enough money to buy these stocks?

        # If everything passes
        #     Subtract from supply's stock counts
        #     Add to players stock counts
        #     Subtract correct amount from player's cash
        for stock in self.stocks:
            if self.state['supply']['stocks'][stock] == 0:
                logger.error("{} buys a {} but supply is empty".format(self.user, stock))
                raise ActionForbiddenException()

            self.state['supply']['stocks'][stock] -= 1
            self.player['stocks'][stock] += 1
            self.player['cash'] -= get_stock_cost(self.state, stock)

            if self.player['cash'] < 0:
                logger.error("{} doesn't have enough money to buy {}".format(self.user, self.stocks))
                raise ActionForbiddenException()

        self.state['history'].append([
            'buy_stocks',
            self.player['username'],
            self.stocks
        ])

        # # Draw Tile
        # Call draw_tile
        # Add drawn tile to players hand
        self.player['tiles'].append(draw_tile(self.state))

        # # End Turn
        # If end_game flag is True
        # Call end_game()  # who knows what goes here?
        if self.state['end_game']:
            self.end_game()
            return self.state

        # Else
        # Set state to "play_tile,next_player()"  # where do we change state.current_player? maybe only need it globally for merging so merging_player?
        # Notify other players
        self.state['state'] = {
            'state': 'play_tile',
            'player': next_player(self.state)
        }

        GameState.objects.create(game=self.game, state=json.dumps(self.state))
        return self.state


class DisposeStockAction(TurnAction):
    def __init__(self, game_pk, user, cart):
        super(DisposeStockAction, self).__init__(game_pk, user)
        self.cart = cart

    def process(self):
        #     {"sell": 0, "trade": 4}  # rest are assumed "keep"

        # So much to check:
        #     Does this player have this much total stock in this chain
        defunct_chain = self.state['merging_chains'][-1]
        winner_chain = self.state['merging_chains'][0]

        if self.player['stocks'][defunct_chain] < (self.cart['trade'] + self.cart['sell']):
            logger.error("{} tries to dispose more shares than in hand {}".format(self.player['username'], self.cart))
            raise ActionForbiddenException()
        #     If trade, is trade count even?
        if self.cart['trade'] % 2 != 0:
            logger.error("{} sent odd trade count {}".format(self.player['username'], self.cart))
            raise ActionForbiddenException()
        #     If trade, is there enough in supply to trade for?
        if self.cart['trade'] / 2 > self.state['supply']['stocks'][winner_chain]:
            logger.error("{} trades for more than supply has {}".format(self.player['username'], self.cart))
            raise ActionForbiddenException()

        # If everything passes
        #     Add sell * chain_value to player's cash
        #     Add sell count to supply
        #     Subtract player's count by sell count
        self.player['cash'] += self.cart['sell'] * get_stock_cost(self.state, defunct_chain)
        self.player['stocks'][defunct_chain] -= self.cart['sell']
        self.state['supply']['stocks'][defunct_chain] += self.cart['sell']

        #     Add trade / 2 shares of winner (merging_chains[0]) stock to player
        #     Subtract trade shares from player
        self.player['stocks'][winner_chain] += self.cart['trade'] / 2
        self.player['stocks'][defunct_chain] -= self.cart['trade']
        self.state['supply']['stocks'][winner_chain] -= self.cart['trade'] / 2
        self.state['supply']['stocks'][defunct_chain] += self.cart['trade']

        #     Anything left is kept by player
        self.state['history'].append([
            'dispose_stock',
            self.player['username'],
            defunct_chain,
            self.cart,
            self.player['stocks'][defunct_chain]
        ])

        self.advance_to_next_dispose_stock()

        GameState.objects.create(game=self.game, state=json.dumps(self.state))
        return self.state


class DetermineWinnerAction(TurnAction):
    def __init__(self, game_pk, user, chains):
        super(DetermineWinnerAction, self).__init__(game_pk, user)
        self.chains = chains

    def process(self):
        # So much to check:
        #     Does set(requested_order) == set(merging_chains from DB's copy of state)?
        if set(self.chains) != set(self.state['merging_chains']):
            logger.error("{} sends invalid chains to determin winner {}".format(self.player['username'], self.chains))
            raise ActionForbiddenException()
        #     Are any of the defunct chains in this order safe? Invalid if so
        for chain in self.chains[1:]:
            if self.state['chains'][chain] > 11:
                logger.error("{} can not be defunct, it is safe".format(chain))
                raise ActionForbiddenException()

        self.state['history'].append([
            'determine_winner',
            self.player['username'],
            self.chains
        ])

        # Call prepare_merger(requested_order)
        self.state['merging_chains'] = self.chains
        self.prepare_merger(self.state)

        GameState.objects.create(game=self.game, state=json.dumps(self.state))
        return self.state


class GetStateAction(Action):
    def __init__(self, game_pk, user):
        super(GetStateAction, self).__init__(game_pk, user)

    def process(self):
        return self.state


class EndGameAction(TurnAction):
    def __init__(self, game_pk, user):
        super(EndGameAction, self).__init__(game_pk, user)

    def process(self):
        # check that either all chains are safe or one chain has >= 41 hotels
        all_safe = all([self.state['chains'][c] >= 11 or self.state['chains'][c] == 0 for c in self.state['chains']])
        over_41 = any([self.state['chains'][c] >= 41 for c in self.state['chains']])

        if not all_safe and not over_41:
            logger.error("{} calls for end of game but conditions not met".format(self.player['username']))
            raise ActionForbiddenException()

        self.state['end_game'] = True

        GameState.objects.create(game=self.game, state=json.dumps(self.state))
        return self.state


# def play_tile(game_pk, user, tile):
#     """Play a tile from a player hand to the board."""
#     # Check that this game exists and this user is in it
#     game = user.game_set.filter(pk=game_pk)
#     if not game.exists():
#         logger.error("{} not in game {}".format(user.username, game_pk))
#         return {
#             "status": 403
#         }  # who knows?
#     game = game[0]  # must be only one because pk is unique
#     state = game.get_active_state()

#     if state['state']['player'] != user.username:
#         logger.error('{} sent a play but it is not their turn'.format(user.username))
#         return {
#             "status": 403
#         }

#     new_state = state__play_tile(state, user, tile)
#     GameState.objects.create(game=game, state=json.dumps(new_state))
#     return new_state


def next_player(state):
    i = [p['username'] for p in state['players']].index(state['state']['player'])
    return state['players'][(i + 1) % len(state['players'])]['username']


def get_neighboring_tiles(tile):
    neighboring_tiles = []
    if tile[0] != "A":
        neighboring_tiles.append(chr(ord(tile[0]) - 1) + tile[1:])
    if tile[0] != "I":
        neighboring_tiles.append(chr(ord(tile[0]) + 1) + tile[1:])
    if tile[1:] != "1":
        neighboring_tiles.append(tile[0] + str(int(tile[1:]) - 1))
    if tile[1:] != "12":
        neighboring_tiles.append(tile[0] + str(int(tile[1:]) + 1))
    return neighboring_tiles


def get_neighboring_assignments(state, tile):
    return [state['hotels'][n] if n in state['hotels'] else None for n in get_neighboring_tiles(tile)]


costs = [200, 200, 200, 300, 400, 500, 600, 600, 600, 600, 600, 700, 700, 700, 700, 700, 700, 700, 700, 700, 700, 800, 800, 800, 800, 800, 800, 800, 800, 800, 800, 900, 900, 900, 900, 900, 900, 900, 900, 900, 900, 1000]


def get_stock_cost(state, chain):
    count = state['chains'][chain]

    if count > 41:
        count = 41

    initial = costs[count]

    if chain == "American" or chain == "Worldwide" or chain == "Festival":
        return initial + 100
    elif chain == "Imperial" or chain == "Continental":
        return initial + 200
    return initial


def convert_islands(state, chain):
    size = 0
    neighboring_hotels = [t for t in get_neighboring_tiles(state['active_cell']) if t in state['hotels'] and state['hotels'][t] == "island"]
    while neighboring_hotels:
        # Assign each hotel to chain
        for hotel in neighboring_hotels:
            state['hotels'][hotel] = chain
            size += 1

        # Pretty sure this converges, assuming that we are correctly forming a chain
        # here which we don't check but play_tile does (hopefully correctly)
        new_neighbors = []
        for hotel in neighboring_hotels:
            island_neighbors = [t for t in get_neighboring_tiles(hotel) if t in state['hotels'] and state['hotels'][t] == "island"]
            new_neighbors += island_neighbors

        neighboring_hotels = island_neighbors
    return size


def declare_chain(game_pk, user, chain):
    """Set the chain for a newly created chain.

    Called AJAXly, client will know to prompt to pick a chain because play_tile set state to "declare_chain"

    Accepts POST only with
        state
        chain

    So much to check:
        Does game exist?
        Is this player in this game?
        Is chain available?

    If it checks out:
        Use active_cell from state, set its chain to "chain"
        Do a crazy search through the board to set all orthogonally adjacent "island" cells to "chain"
        Add one stock of declared chain to player's hand
        Subtract one stock from supply

    Set state to "buy_stocks" and notify all.
    """
    # if 'game_id' not in request.POST or 'chain' not in request.POST:
    #     return HttpResponseBadRequest()

    # game = request.user.game_set.filter(request.POST['game_id'])
    # if not game.exists():
    #     raise PermissionDenied

    # state = json.loads(game.state)

    # if request.POST['chain'] not in [chain for chain in state.chains if chain.size == 0]:
    #     logger.debug("User {} attempted to declare unavailable chain {}".format(request.user, request.POST['chain']))
    #     raise PermissionDenied

    # state.active_cell.chain = request.POST['chain']
    # # do search here

    # notify_all(state)
    pass


def buy_stocks(request):
    """Spend some money to buy stocks for this player.

    Called AJAXly

    Accepts POST only with
        game_id
        player_id
        [stock1, stock2, stock3] OR [stock1] OR []

    So much to check:
        Does game exist?
        Is this player in this game?
        Has this player asked for more than 3 stocks?
        Are these stocks available in the supply?
        Does this player have enough money to buy these stocks?

    If everything passes
        Subtract from supply's stock counts
        Add to players stock counts
        Subtract correct amount from player's cash

    # Draw Tile
    Call draw_tile
    Add drawn tile to players hand

    # End Turn
    If end_game flag is True
    Call end_game()  # who knows what goes here?

    Else
    Set state to "play_tile,next_player()"  # where do we change state.current_player? maybe only need it globally for merging so merging_player?
    Notify other players
    """
    pass


def draw_tile(state):
    """Draw a tile.

    Called from buy_stocks or merger determine_winner. Assumed to be correct thing to do.

    Pick a random number from 0 to size of supply.tiles
    Remove that tile from supply.tiles
    Return drawn tile
    """
    return state['supply']['tiles'].pop()


def pluck_player(state, username):
    return [p for p in state['players'] if p['username'] == username][0]


def determine_winner(request):
    """Set merge winner order in case of ties.

    Called AJAXly

    Accepts POST only with
        state
        [winner, loser3, loser2, loser1] as necessary

    So much to check:
        Does game exist?
        Is this player in this game?
        Does set(requested_order) == set(merging_chains from DB's copy of state)?
        Are any of the defunct chains in this order safe? Invalid if so

    Call prepare_merger(requested_order)

    Notify all.
    """
    pass


def pay_bonuses(state):
    """Pay bonuses for the active merger.

    Assumes everything is fine, just pay the bonuses for the last chain in merging_chains.

    The last chain in merging_chains is the loser.
    Determine maj and min share holders for that chain.

    If this is a two player game
        Pick a tile from the supply and return it
            Pick random number from 0 to supply.tiles.size
            Use that tile
        Use its number as another player for this calculation

    If tie for first:
        Add maj and min bonuses divide evenly among tied players
    Else:
        Pay maj to first
        If tie for second:
            Divide min bonus evenly among tied players
        Else:
            Pay min to second
    """
    defunct_chain = state['merging_chains'][-1]
    majority_bonus = get_stock_cost(state, defunct_chain) * 10
    minority_bonus = majority_bonus / 2

    stock_holders = [p for p in state['players'] if p['stocks'][defunct_chain] > 0]

    if len(state['players']) == 2:
        tile = state['supply']['tiles'][random.randint(0, len(state['supply']['tiles']))]
        stock_holders.append({
            'username': None,
            'stocks': {
                defunct_chain: int(tile[1:])
            },
            'cash': 0
        })

    stock_holders.sort(key=lambda x: x['stocks'][defunct_chain], reverse=True)

    if len(stock_holders) == 1:
        # if there is only one stock holder, they get both bonuses
        bonus = majority_bonus + minority_bonus
        stock_holders[0]['cash'] += bonus
        state['history'].append(['both_bonus', bonus, stock_holders[0]['username'], stock_holders[0]['stocks'][defunct_chain]])
    else:
        equal_to_first = [p for p in stock_holders if p['stocks'][defunct_chain] == stock_holders[0]['stocks'][defunct_chain]]
        if len(equal_to_first) != 1:
            # split bonus
            bonus = (majority_bonus + minority_bonus) / len(equal_to_first)
            # round to nearest $100
            bonus = int(math.ceil(bonus / 100.0)) * 100
            for p in equal_to_first:
                p['cash'] += bonus

            state['history'].append(['majority_bonus', bonus] + [p['username'] for p in equal_to_first] + [stock_holders[0]['stocks'][defunct_chain]])
        else:
            stock_holders[0]['cash'] += majority_bonus
            state['history'].append(['majority_bonus', majority_bonus, stock_holders[0]['username'], stock_holders[0]['stocks'][defunct_chain]])

            equal_to_second = [p for p in stock_holders if p['stocks'][defunct_chain] == stock_holders[1]['stocks'][defunct_chain]]
            if len(equal_to_second) != 1:
                bonus = minority_bonus / len(equal_to_second)
                # round to nearest $100
                bonus = int(math.ceil(bonus / 100.0)) * 100
                for p in equal_to_second:
                    p['cash'] += bonus

                state['history'].append(['minority_bonus', bonus] + [p['username'] for p in equal_to_second] + [stock_holders[1]['stocks'][defunct_chain]])
            else:
                stock_holders[1]['cash'] += minority_bonus
                state['history'].append(['minority_bonus', minority_bonus, stock_holders[1]['username'], stock_holders[1]['stocks'][defunct_chain]])


def dispose_loser_stock(request):
    """Do something with leftover stock of loser chain during merger.

    Called AJAXly during a merger

    Accepts POST only with
        state
        {"sell": 0, "trade": 4}  # rest are assumed "keep"

    So much to check:
        Does game exist?
        Is this player in this game?
        Is it this player's turn? (This is always(?) part of the state?)
        Does this player have this much total stock in this chain
        If trade, is trade count even?
        If trade, is there enough in supply to trade for?

    If everything passes
        Add sell * chain_value to player's cash
        Add sell count to supply
        Subtract player's count by sell count

        Add trade / 2 shares of winner (merging_chains[0]) stock to player
        Subtract trade shares from player

        Anything left is kept by player

    If next_player() is merging_player/current_player (aka everyone has had a turn):
        Remove last chain from merging_chains
        If merging_chains.size() > 1:
            Call pay_bonuses
            Set state to "dispose_stock,state.current_player"
        Else:
            # All merging is done
            Call resolve_merge()
    Else:
        Set state to "dispose_stock,next_player_who_has_stock()"

    Notify all.
    """
    pass


def resolve_merge(state):
    """Change all merging hotels to the winner chain.

    Assumes this is called at the right time and is the right thing to do.

    """
    #     Winning chain is merging_chains[0]
    winner_chain = state['merging_chains'][0]

    # Set active_cell to winning chain
    state['hotels'][state['active_cell']] = winner_chain

    # For each cell on board:
    #     If cell belongs to defunct chain
    #         Set cell to winning chain
    for cell, chain in state['hotels'].items():
        if chain in state['defunct_chains']:
            state['hotels'][cell] = winner_chain

    # Add to size of winning chain the sizes of all defunct chains + 1
    # Set size of defunct chains to 0
    size = 1
    for defunct_chain in state['defunct_chains']:
        size += state['chains'][defunct_chain]
        state['chains'][defunct_chain] = 0

    size += convert_islands(state, winner_chain)
    state['chains'][winner_chain] += size

    # Set defunct chains to []
    # Set merging chains to []
    state['defunct_chains'] = []
    state['merging_chains'] = []
