var fsm;

// Read JSON data provide by Django json_script template tag
var initialState = JSON.parse(document.getElementById('initial-state').textContent);

/***************************
 * websocket
 **************************/

var websocketURL = ((location.protocol == 'https:') ? "wss" : "ws") + "://" + window.location.host + '/ws/matcha/' + initialState.game_name + '/';

var chatSocket = new ReconnectingWebSocket(websocketURL);

chatSocket.addEventListener('message', function(e) {
    var data = JSON.parse(e.data);
    console.log(data);

    if ("status" in data) {
        console.log("Possibly something has gone wrong");
        // app.instruction += " Error status: " + data.status + " " + data.text;
    } else {
        fsm.transition('uninitialized');
        fsm.handle('initialize', data);
    }
});

var firstOpenListener = function (e) {
    chatSocket.removeEventListener('open', firstOpenListener);
    chatSocket.addEventListener('open', function (e) {
        console.log("socket has reconnected, need to ask for current state");
        if (fsm.active != 'end_game') {
            chatSocket.send(JSON.stringify({
                action: 'get_state'
            }));
        } else {
            chatSocket.close();
        }
    });
}

chatSocket.addEventListener('open', firstOpenListener);

chatSocket.addEventListener('close', function(e) {
    console.error('Chat socket closed unexpectedly');
});

/***************************
 * Card class
 **************************/

function Card(obj) {
  this.suit = obj.suit;
  this.rank = obj.rank;
  this.class = this.toClass();
}

Card.prototype.toData = function () {
  return {
    suit: this.suit,
    rank: this.rank,
  };
}

Card.prototype.SUITS = {
  1: 'clubs',
  2: 'spades',
  3: 'hearts',
  4: 'diamonds',
};

Card.prototype.RANKS = {
  11: 'ace',
  10: 'ten',
  4: 'king',
  3: 'queen',
  7: 'seven',
};

Card.prototype.SUIT_STR = {
  1: "♣",
  2: "♠",
  3: "♥",
  4: "♦",
};

Card.prototype.RANK_STR = {
  11: "A",
  10: "10",
  4: "K",
  3: "Q",
  7: "7",
};

Card.prototype.toClass = function () {
  return "playing-card " + Card.prototype.SUITS[this.suit];
}

Card.prototype.toString = function () {
  return Card.prototype.SUIT_STR[this.suit] + Card.prototype.RANK_STR[this.rank];
}

Card.prototype.sort = function (a, b) {
  // return negative number if a < b
  if (a.suit != b.suit) {
    return a.suit - b.suit;
  }
  return ((b.rank == 7) ? 1 : b.rank) - ((a.rank == 7) ? 1 : a.rank);
}

Card.prototype.play = function (event, model) {
  console.log("Would like to play", model.card);
  fsm.handle('play_card', model.card);
}

/***************************
 * rivetsjs app
 **************************/

var app = {
  hand: [],
};

/***************************
 * machinajs finite state machine
 **************************/

var fsm = new machina.Fsm({
  initialize: function(options) {
      // your setup code goes here...
  },
  namespace: "matcha",
  initialState: "uninitialized",
  states: {
    uninitialized: {
      initialize: function (initialState) {
        // Save current server state
        this.matcha = initialState;

        // active should be true if websocket should be connected
        this.active = this.matcha.state.state != "match_ended";

        var me = this.pluckPlayer(initialState.me);
        // load hand
        app.hand = me.hand.map(function (card) {
          return new Card(card);
        }).sort(Card.prototype.sort);

        if (this.matcha.state.player == this.matcha.me) {
          this.transition(this.matcha.state.state);
        } else {
          this.transition('waiting');
        }
      }
    },

    foreplace: {
      _onEnter: function () {
        app.instruction = "Choose a card to foreplace or skip."
      },
      play_card: function (card) {
        console.log("Tell server to foreplace ", card);
        chatSocket.send(JSON.stringify({
            action: 'foreplace',
            body: card.toData()
        }));
      }
    },

    waiting: {
      _onEnter: function () {
        app.instruction = 
          "Waiting for " + 
          this.matcha.state.player + 
          " to " +
          this.stateToInstruction(this.matcha.state.state) +
          ".";
      }
    },
  },

  pluckPlayer: function (playerName) {
    var list = this.matcha.players.filter(function (player) {
      return player.name == playerName;
    });
    return (list.length > 0) ? list[0] : null;
  },

  stateToInstruction: function (state) {
    const stateMap = {
      'foreplace': 'foreplace a card'
    };
    return (state in stateMap) ? stateMap[state] : state;
  },
});

/***************************
 * Page load handlers
 **************************/

document.addEventListener("DOMContentLoaded", function() {
  fsm.handle('initialize', initialState);
  rivets.bind(document.getElementById("main"), {app: app});
});

/***************************
 * rivetsjs formatters
 **************************/

rivets.formatters.card = function(value){
  return value.toString();
}
