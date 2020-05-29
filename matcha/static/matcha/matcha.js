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
    console.log("MESSAGE", data);

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
 * EmptyCard class
 **************************/

function EmptyCard() {
  this.class = "playing-card empty";
}

EmptyCard.prototype.toString = function () {
  return " ";
}

/***************************
 * EmptyCard class
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
 * Player
 **************************/

function Player(data) {
  this.name = data.name;
  this.foreplace = data.foreplace.length > 0 ? new Card(data.foreplace[0]) : new EmptyCard();
  this.tableau = _.range(10).map(function (i) {
    return i < data.tableau.length ? new Card(data.tableau[i]) : new EmptyCard();
  });
  this.score = data.score;
}

Player.prototype.isMe = function () {
  return this.name == fsm.matcha.me;
}

/***************************
 * rivetsjs app
 **************************/

var app = {
  hand: [],
  skipForeplace: function () {
    fsm.handle("skip_foreplace");
  },
  nextGame: function () {
    fsm.handle("next_game");
  }
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
        me.hand = me.hand.map(function (card) {
          return new Card(card);
        }).sort(Card.prototype.sort);

        app.hand = _.range(10).map(function (i) {
          return i < me.hand.length ? new Card(me.hand[i]) : new EmptyCard();
        });

        this.matcha.players.forEach(function (data) {
          var player = new Player(data);
          if (player.isMe()) {
            app.me = player;
          } else {
            app.opponent = player;
          }
        });

        if (this.matcha.state.player == this.matcha.me || this.matcha.state.state == 'matcha') {
          this.transition(this.matcha.state.state);
        } else {
          this.transition('waiting');
        }

        app.gameNumber = this.matcha.state.game_id + 1;
      }
    },

    foreplace: {
      _onEnter: function () {
        app.instruction = "Choose a card to foreplace or skip.";
        app.showSkipForeplace = true;
      },
      play_card: function (card) {
        console.log("Tell server to foreplace ", card);
        chatSocket.send(JSON.stringify({
            action: 'foreplace',
            body: card.toData()
        }));
      },
      skip_foreplace: function (card) {
        console.log("Tell server to skip foreplace");
        chatSocket.send(JSON.stringify({
            action: 'skip_foreplace',
            body: {}
        }));
      },
      _onExit: function () {
        app.instruction = '';
        app.showSkipForeplace = false;
      }
    },

    lead: {
      _onEnter: function () {
        app.instruction = 'Lead a card.';
      },

      play_card: function (card) {
        console.log("Tell server to lead ", card);
        chatSocket.send(JSON.stringify({
            action: 'lead',
            body: card.toData()
        }));

      },

      _onExit: function () {
        app.instruction = '';
      }
    },

    follow: {
      _onEnter: function () {
        app.instruction = "Follow your opponent's card.";
      },

      play_card: function (card) {
        console.log("Tell server to follow with ", card);
        chatSocket.send(JSON.stringify({
            action: 'follow',
            body: card.toData()
        }));
      },

      _onExit: function () {
        app.instruction = '';
      }
    },

    matcha: {
      _onEnter: function () {
        app.instruction = "It's a matcha!"
        app.showNextGame = true;
      },

      next_game: function () {
        chatSocket.send(JSON.stringify({
            action: 'next_game',
            body: app.me.name
        }));
      },

      _onExit: function () {
        app.instruction = '';
        app.showNextGame = false;
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
      },
      _onExit: function () {
        app.instruction = '';
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

rivets.formatters.card = function(value) {
  return value ? value.toString() : value;
}
