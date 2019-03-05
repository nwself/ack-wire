import json
import logging

from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest
from django.shortcuts import render
from django.utils.safestring import mark_safe


logger = logging.getLogger(__file__)


def game(request, game_name):
    return render(request, 'game/game.html', {
        'game_name_json': mark_safe(json.dumps(game_name))
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


def start_game(players):
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
    pass


def notify_all(state):
    """Send the new state to everyone.

    Each player needs a subset of the total state so they don't get each other tiles.

    Send whole state except remove supply.tiles and player.tiles for everyone but recipient.
    """
    pass


def end_game(request):
    """Set the end game flag on the state to end the game after the current turn.

    Will be called AJAXly

    So much to check:
        Look for game_id in request.user.game_set

    Check that either one chain has >=41 hotels or all active chains are safe
        If so set end_game flag on state
        Else => 403
    """
    pass


def play_tile(request):
    """Play a tile from a player hand to the board.

    Will be called AJAXly

    Accepts POST only with
        request.user
        game_id
        tile to lay

    So much to check:
        Look for game_id in request.user.game_set
        If not there:
            Return 403

        Does this player have this tile in hand? (if not => 403)
        Is this tile a legal play?
            already in hand implies that the space is free but it could be unplayable via safe chains
            Check if this mergers safe chains
            Check if this creates a chain when there are no chains available

    If everything checks out
        Place tile on board
            Find cell in state.cells
            Set active_cell to it
            Check orthonal cells
            If all have chain == None:
                Set cell chain to island
            If all have chain == None or chain == "island":
                if there are available chains in the supply:
                    Change state to declare_chain and return from here as normal
                else:
                    Return unplayable tile error
            If all have chain == None or chain == some_chain:
                Set cell chain to some_chain
            if some have chain == chain1 and others chain == chain2:
                if chain1 and chain2 are safe:
                    This is an unplayable tile (do we auto-remove these?)
                    Return unplayable tile error
                else
                    Change state to merger
                    state = start_merger_helper(state, cell)

    If state not yet changed, change to "buy_stocks"
    Return new state and notify other players of state change! (sockets?)
    """
    pass


def declare_chain(request):
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
    if 'game_id' not in request.POST or 'chain' not in request.POST:
        return HttpResponseBadRequest()

    game = request.user.game_set.filter(request.POST['game_id'])
    if not game.exists():
        raise PermissionDenied

    state = json.loads(game.state)

    if request.POST['chain'] not in [chain for chain in state.chains if chain.size == 0]:
        logger.debug("User {} attempted to declare unavailable chain {}".format(request.user, request.POST['chain']))
        raise PermissionDenied

    state.active_cell.chain = request.POST['chain']
    # do search here

    notify_all(state)


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


def draw_tile(request):
    """Draw a tile.

    Called from buy_stocks or merger determine_winner. Assumed to be correct thing to do.

    Pick a random number from 0 to size of supply.tiles
    Remove that tile from supply.tiles
    Return drawn tile
    """
    pass


def start_merger_helper(state, cell):
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
    pass


def prepare_merger(merging_order):
    """Modify state to start mergering.

    Set merging_chains on state to match requested order
    Set defunct_chains to merging_chains[1:]

    Call pay_bonuses (should pay for first merger)
    Set state to "dispose_loser,current_player"
    """
    pass


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
    pass


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

    Winning chain is merging_chains[0]
    Set active_cell to winning chain
    For each cell on board:
        If cell belongs to defunct chain
            Set cell to winning chain

    Add to size of winning chain the sizes of all defunct chains + 1
    Set size of defunct chains to 0
    Set defunct chains to []
    Set merging chains to []

    Set state to "buy_stock,merging_player"
    """
    pass
