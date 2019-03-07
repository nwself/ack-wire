var fsm;

var chatSocket = new WebSocket(
    'ws://' + window.location.host +
    '/ws/chat/' + roomName + '/');

chatSocket.onmessage = function(e) {
    var data = JSON.parse(e.data);
    console.log(data);

    if ("status" in data) {
        console.log("Possibly something has gone wrong");
    } else {
        fsm.handleNewState(data);
    }

    // var message = data['message'];
    // document.querySelector('#chat-log').value += (message + '\n');
};

chatSocket.onclose = function(e) {
    console.error('Chat socket closed unexpectedly');
};


var app = {
    board: [],
    hand: [],
    instruction: '',
    play_tile: function () {
        console.log(arguments);
    }
};


var fsm = new machina.Fsm({
    initialize: function(options) {
        // your setup code goes here...
    },
    namespace: "acquire",
    initialState: "uninitialized",
    states: {
        'uninitialized': {
            // "*": function() {
            //     this.deferUntilTransition();
            //     this.transition( "green" );
            // }
        },
        'play_tile': {
            _onEnter: function() {
                app.instruction = "Choose a tile to play.";
            },

            'tile_clicked': function (tile) {
                console.log("Here in the FSM with this tile", tile);
                chatSocket.send(JSON.stringify({
                    action: 'play_tile',
                    body: {
                        tile: tile.coordinates
                    }
                }));
            }
        },
        'declare_chain': {
            _onEnter: function () {
                app.instruction = "Name your newly formed chain.";

                app.showAvailableChains = true;
                app.availableChains = Object.keys(fsm.acquire.chains).map(function (chainName) {
                    return new Chain({
                        name: chainName,
                        size: fsm.acquire.chains[chainName]
                    });
                }).filter(function (chain) {
                    return chain.size == 0;
                });
            },

            'chain_clicked': function (chain) {
                console.log("Here in FSM with this chain", chain);
                chatSocket.send(JSON.stringify({
                    action: 'declare_chain',
                    body: {
                        chain: chain.name
                    }
                }));
            },

            _onExit: function () {
                app.showAvailableChains = false;
            }
        }
    },

    handleNewState: function (acquire) {
        fsm.acquire = acquire;

        app.board = [];
        app.hand = [];

        var letters = ["A", "B", "C", "D", "E", "F", "G", "H", "I"];
        for (var i = 0; i < letters.length; i++) {
            var row = [];
            for (var j = 0; j < 12; j++) {
                var coordinates = letters[i] + (j + 1);
                row.push(new Cell({
                    coordinates: coordinates,
                    chain: ((coordinates in acquire.hotels) ? acquire.hotels[coordinates] : null),
                }));
            }
            app.board.push(row);
        }


        var thisPlayer = acquire.players.filter(function (player) {
            return player.username === username;
        });

        if (thisPlayer.length !== 0) {
            thisPlayer = thisPlayer[0];
            app.hand = thisPlayer.tiles.sort().map(function (coordinates) {
                return new Tile({
                    coordinates: coordinates
                });
            });
        } else {
            thisPlayer = null;
        }


        if (acquire.state.player == username) {
            this.transition(acquire.state.state);
        } else {
            this.transition("waiting");
            app.instruction = "Waiting for " + acquire.state.player + " to " + acquire.state.state;
        }
    },

    chainClicked: function (chain) {
        this.handle('chain_clicked', chain);
    },

    tileClicked: function (tile) {
        this.handle('tile_clicked', tile);
    },
});


function Cell(obj) {
    this.coordinates = obj.coordinates;
    this.chain = obj.chain;

    if (this.chain) {
      console.log(this.coordinates, this.chain);
    }
}


function Tile(obj) {
    this.coordinates = obj.coordinates;
}

Tile.prototype.play = function (event, model) {
    console.log("Would like to play", model.tile.coordinates);
    fsm.tileClicked(model.tile);
}


function Chain(obj) {
    this.name = obj.name;
    this.size = obj.size;
}

Chain.prototype.declare = function (event, model) {
    console.log("Would like to declare", model.chain.name);
    fsm.chainClicked(model.chain);
}


fsm.handleNewState(state);


document.addEventListener("DOMContentLoaded", function() {
    rivets.bind(document.getElementById("main"), {app: app});
});

// // represents the stata and is synced with/bound to the HTML rivets template
// var app = {
//   board: null,
//   supply: {
//     tiles: 108,
//     stocks: {  // keys must match "chains"
//       "American": 25,
//       "Worldwide": 25
//     }
//   },
//   chains: {  // chain names and their size, if 0 chain is available/not active
//     "American":{
//       size: 0,
//       staged: 0, // for buying stocks, maybe??
//     },
//     "Worldwide": 0
//   },
//   players: {
//     "name": {
//       cash: 100,
//       stocks: {
//         "American": 0,
//         "Worldwide": 0
//       }
//     }, // and so on...
//   },
//   me: {  // "me" is kind of anemic
//     cash: 100,
//     stocks: {},
//     tiles: [
//       "A4",
//       "I12",  // and so on...
//     ]
//   }
// };


// function Chain() {
//   // class to represent chains
//   // somehow these things need to be instantiated from the state which we receive from
//   // the server after each update
//   size: 0,
//   active: function () {
//     return this.size > 0;
//   }
// }

// function StagedChain() {
//   // not sure how we'll make these, needed for buying stocks, some kind of rivets template/model

//   increment: function () {
//     // check that this chain is available in supply
//     // check that player has money for this purchase
//     // this.count++ (should update view)
//     // global purchase_price += cost  (not sure where purchase price will live)
//   }
// }

// var game = new machina.Fsm({
//   initialize: function() {
//   },

//   namespace: "acquire-game",

//   initialState: "???",

//   states: {
//     'play-tile': function () {
//       // show board (always???)
//       // show tiles
//       // show instruction: Play a tile
//       //
//       // state needs to have 
//       //   board
//       //   current player tiles, stocks, cash
//       //   all players stock and cash
//       //   supply # tiles left, stocks avail, chains avail
//       //
//       // go to this state when statestate is "play_tile,thisplayer"
//       //
//       // on click of tile in hand, prompt for validation, then send play_tile AJAX
//       //
//       // tile.onclick should call handle tile clicked on the fsm
//       // this state should handle tileClicked events but others may not
//     },

//     'buy-stocks': function () {
//       // go here when state is "buy_stock,thisplayer"
//       // at some point call buy_stock AJAXly with the answer (on validate)

//       _onEnter: function () {
//         // change app.showStockStaging to true?? or maybe it's based on stateName
//         //
//         // create app.stagingStocks
//         //    for each chain in chains if size > 0
//         //        map to new StagingStock(chain, price)
//         //        StagingStock will be a cool rivets component that handles +/- itself


//         // show chain purchase in staging area
//         // template should be
//         // rv-each-chain="app.chains"
//         //    could use custom elements from rivets
//         //    <staging-chain rv-show="chain.active()">
//         //
//         // staging-chain shows image, underneath - 0 + for buying it
//         //
//         // each + is only enabled if there is a stock available and player can afford 1
//         // each - is only enabled if staged purchase of this stock is > 0
//       },

//       plusClicked: function (stagedChain) {
//         // how do we know which chain's plus was clicked here? model from click callback passed to here?
//         // need to double check that this chain is active? probably not?

//         // acting on StagedChain objects here?
//         // stagedChain.increment()
//       },

//       minusClicked: function (stagedChain) {
//         // same as above
//         // stagedChain.decrement()
//       }

//       _onExit: function () {
//         // hide staging area?
//       },
//     },

//     'declare-chain': function () {
//       // this state is for picking an available chain for a newly created chain
//       //
//       // expect user to
//       //    choose an available chain from the action area
//       //    click validate to send to server

//       _onEnter: function () {
//         // show stuff?

//         // show pick-chain element which is rv-show=fsm.state=='declare-chain' so it's automatic
//         // pick-chain element should have a chain image for each available chain
//         //    <img rv-show=chain.size>0 src=chain.img>
//         // onclick for the chain image should highlight it
//         //    app.declared_chain=chain
//         // validate button should become enabled declared_chain != null
//         // validate onclick should hit declare_chain AJAX, hide the stuff, wait for new state

//         // in theory if a bad request is sent, server should respond with previous state in 
//         // an attempt to try again
//       },

//       _onExit: function () {
//         // hide stuff??
//         // possibly this is all automatic because rv-show works on app.state?
//       }
//     },

//     'determine-winner': function () {
//       // this state is for choosing which merging chain in the case of a tie
//       // 
//       // not sure how to display this
//       // some winners component

//       _onEnter: function () {
        
//       }
//     },

//     'dispose-stock': function () {
//       // choose to sell, trade, keep stock of loser during a merger
//       //
//       // validate onclick should hit 'dispose_loser_stock' AJAX, wait for new state
//     }
//   },
// });

// // Need a end game button somewhere that hits the 'end_game' AJAX, then
// // waits for new state which should be the same but with end game checked?

// // Got a new state on the socket from the server, update everything
// function replaceState(state) {
//   // This function needs to replace all of (or the components of) app to refresh the page

//   // Replace board, supply, chains, players, me
//   // transition fsm to state requested by state
// }
