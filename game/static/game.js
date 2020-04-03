var fsm;

var websocketURL = ((location.protocol == 'https:') ? "wss" : "ws") + "://" + window.location.host + '/ws/chat/' + roomName + '/';

var chatSocket = new ReconnectingWebSocket(websocketURL);

chatSocket.addEventListener('message', function(e) {
    var data = JSON.parse(e.data);
    console.log(data);

    if ("status" in data) {
        console.log("Possibly something has gone wrong");
        app.instruction += " Error status: " + data.status + " " + data.text;
    } else {
        fsm.handleNewState(data);
    }
});

var firstOpenListener = function (e) {
    chatSocket.removeEventListener('open', firstOpenListener);
    chatSocket.addEventListener('open', function (e) {
        console.log("socket has reconnected, need to ask for current state");
        if (fsm.acquire.state.state != 'end_game') {
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

function array_move(arr, old_index, new_index) {
    if (new_index >= arr.length) {
        var k = new_index - arr.length + 1;
        while (k--) {
            arr.push(undefined);
        }
    }
    arr.splice(new_index, 0, arr.splice(old_index, 1)[0]);
    return arr; // for testing
};

var stockCosts = [200, 200, 200, 300, 400, 500, 600, 600, 600, 600, 600, 700, 700, 700, 700, 700, 700, 700, 700, 700, 700, 800, 800, 800, 800, 800, 800, 800, 800, 800, 800, 900, 900, 900, 900, 900, 900, 900, 900, 900, 900, 1000];

var app = {
    board: [],
    hand: [],
    playerStocks: [],
    players: [],
    instruction: '',
    stocksCart: [],
    showDisposeStocks: false,
    gameEnded: false,
    showEndGame: false,
    stockDisposer: new StockDisposer({merging_chains: ["Luxor"]}), // need a dummy because rivets parses the whole thing on startup
    play_tile: function () {
        console.log(arguments);
    },
    buyStocks: function () {
        console.log(arguments);
        fsm.buyStocks();
    },
    determineWinner: function () {
        fsm.determineWinner();
    },
    totalCost: function () {
        return app.stocksCart.reduce(function (prev, stock) {
            return prev + app.lookupChainCost(stock.name);
        }, 0);
    },
    canAddStock: function (stock) {
        return (app.stocksCart.length < 3) && 
            (app.lookupChainCost(stock.name) + app.totalCost() <= app.player.cash) &&
            (fsm.acquire.supply.stocks[stock.name] > app.cartCount(stock));
            // (app.supply.stocks[stock.name] )
            // TODO also need to check that there are enough in the supply here
    },
    hasNone: function (stock) {
        return app.stocksCart.filter(function (s) {
            return stock.name == s.name;
        }).length == 0;
    },
    isZero: function (number) {
        return number == 0;
    },
    lookupChainCost: function(chainName) {
        var count = fsm.acquire.chains[chainName];

        if (count > 41) {
            count = 41;
        }

        var initial = stockCosts[count];

        if (chainName === "American" || chainName === "Worldwide" || chainName === "Festival") {
            return initial + 100;
        } else if (chainName === "Imperial" || chainName === "Continental") {
            return initial + 200;
        }
        console.log("Cost for", chainName, initial);
        return initial;
    },
    cartCount: function (stock) {
        return app.stocksCart.reduce(function (prev, s) {
            return prev + ((s.name == stock.name) ? 1 : 0);
        }, 0);
    },
    getShareCount: function (playerName, chain) {
        var players = app.players.filter(function (player) {
            return player.name == playerName;
        });
        if (players.length == 0) {
            return 0;
        }
        return (chain in players[0].stocks) ? players[0].stocks[chain] : 0;
    },
    endGame: function () {
        fsm.endGame();
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
        },
        'buy_stocks': {
            _onEnter: function () {
                app.instruction = "Buy stocks.";

                app.stocksCart = [];
                app.showAvailableStocks = true;
                app.availableStocks = Object.keys(fsm.acquire.chains).filter(function (chainName) {
                    return fsm.acquire.chains[chainName] > 0;
                }).map(function (chainName) {
                    return new Stock({
                        name: chainName,
                        available: fsm.acquire.supply.stocks[chainName],
                        size: fsm.acquire.chains[chainName]
                    })
                })
            },

            'buy_stocks': function () {
                var stocks = app.stocksCart.map(function (stock) {
                    return stock.name;
                });
                console.log("Here in fsm buying stocks", stocks);
                chatSocket.send(JSON.stringify({
                    action: 'buy_stocks',
                    body: {
                        stocks: stocks
                    }
                }));
            },

            _onExit: function () {
                app.showAvailableStocks = false;
            }
        },
        'dispose_stock': {
            _onEnter: function () {
                app.instruction = "Dispose of stock in the defunct chain."

                app.showDisposeStocks = true;
                app.stockDisposer = new StockDisposer(fsm.acquire);
            },

            'dispose_stock': function (cart) {
               console.log("Here in fsm disposing stocks", cart);
               chatSocket.send(JSON.stringify({
                   action: 'dispose_stocks',
                   body: {
                       cart: cart
                   }
               }));
            },

            _onExit: function () {
                app.showDisposeStocks = false;
            }
        },
        'determine_winner': {
            _onEnter: function () {
                app.instruction = "Determine winner of merger."

                app.showDetermineWinner = true;
                app.mergingChains = fsm.acquire.merging_chains.map(function (chainName, i) {
                    return {
                        order: i + 1,
                        name: chainName,
                        size: fsm.acquire.chains[chainName],
                        canUp: function (chain) {
                            var index = chain.order - 1;
                            return index != 0 && app.mergingChains[index].size >= app.mergingChains[index-1].size;
                        },
                        up: function (event, model) {
                            var index = model.chain.order - 1;
                            var newChains = app.mergingChains.slice();
                            array_move(newChains, index, index - 1);
                            newChains[index].order++;
                            newChains[index - 1].order--;
                            app.mergingChains = newChains; 
                        },
                        canDown: function (chain) {
                            var index = chain.order - 1;
                            return index != app.mergingChains.length-1 && app.mergingChains[index].size <= app.mergingChains[index+1].size;
                        },
                        down: function (event, model) {
                            var index = model.chain.order - 1;
                            var newChains = app.mergingChains.slice();
                            array_move(newChains, index, index + 1);
                            newChains[index].order--;
                            newChains[index + 1].order++;
                            app.mergingChains = newChains;
                        }
                    }
                });
            },

            'determine_winner': function () {
                var winnerOrder = app.mergingChains.map(function (chain) {
                    return chain.name;
                });
                console.log("Here in fsm determining winner", winnerOrder);
                chatSocket.send(JSON.stringify({
                    action: 'determine_winner',
                    body: {
                        chains: winnerOrder
                    }
                }));
            },

            _onExit: function () {
                app.showDetermineWinner = false;
            }
        },
        'end_game': {
            _onEnter: function () {
                var instruction = "Game over."
                fsm.acquire.players.sort(function (a, b) {
                    return b.cash - a.cash;
                })
                fsm.acquire.players.forEach(function (player) {
                    instruction += " " + player.username + ": $" + player.cash;
                });
                app.instruction = instruction;
            }
        },
        'waiting': {

        }
    },

    handleNewState: function (acquire) {
        fsm.acquire = acquire;

        app.board = [];
        app.hand = [];

        app.player = acquire.players.filter(function (player) {
            return player.username === username;
        });

        if (app.player.length !== 0) {
            app.player = app.player[0];
            app.hand = app.player.tiles.map(function (coordinates) {
                // side effect time
                acquire.hotels[coordinates] = 'in-hand';

                return new Tile({
                    coordinates: coordinates
                });
            });
        } else {
            app.player = null;
        }

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

        app.players = acquire.players.map(function (player) {
            return new Player(player);
        });

        app.playerStocks = Object.keys(app.player.stocks).filter(function (stockName) {
            return app.player.stocks[stockName] > 0;
        }).map(function (stockName) {
            return {
                name: stockName,
                count: app.player.stocks[stockName],
                swatch: stockName + " swatch"
            };
        });

        app.supplyStocks = Object.keys(acquire.supply.stocks).map(function (stockName) {
            return new Stock({
                name: stockName,
                count: acquire.supply.stocks[stockName],
                size: acquire.chains[stockName]
            });
        });

        app.history = acquire.history.reverse();

        if (acquire.state.player == username || acquire.state.player == '') {
            app.myturn = true;
            this.transition(acquire.state.state);
        } else {
            this.transition("waiting");
            app.instruction = "Waiting for " + acquire.state.player + " to " + acquire.state.state;
        }

        fsm.checkForEnd(acquire.chains);
    },

    checkForEnd: function (chains) {
        var allSafe = Object.keys(chains).reduce(function (prev, chainName) {
            return prev && (chains[chainName] >= 11 || chains[chainName] == 0);
        }, true) && !Object.keys(chains).reduce(function (prev, chainName) {
            return prev && chains[chainName] == 0;
        }, true);
        var over41 = Object.keys(chains).reduce(function (prev, chainName) {
            return prev || chains[chainName] >= 41;
        }, false);
        if (allSafe || over41) {
            console.log("allSafe", allSafe, "over41", over41);
            app.showEndGame = true;
        }
        app.gameEnded = fsm.acquire.end_game;
    },

    chainClicked: function (chain) {
        this.handle('chain_clicked', chain);
    },

    tileClicked: function (tile) {
        this.handle('tile_clicked', tile);
    },

    buyStocks: function () {
        this.handle('buy_stocks');
    },

    disposeStock: function (cart) {
        this.handle('dispose_stock', cart);
    },

    determineWinner: function (cart) {
        this.handle('determine_winner');
    },

    endGame: function () {
        console.log("Calling for end of game");
        chatSocket.send(JSON.stringify({
            action: 'end_game',
            body: {}
        }));
    }
});

function Player(obj) {
    this.name = obj.username;
    this.stocks = obj.stocks;
    this.cash = obj.cash;
    this.isme = app.player.username == this.name;
}

function Cell(obj) {
    this.coordinates = obj.coordinates;
    this.chain = obj.chain;
}

Cell.prototype.play = function (event, model) {
    if (event.target.classList.contains('in-hand')) {
        fsm.tileClicked(model.cell);
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
    this.swatch = this.name + " swatch";
}

Chain.prototype.declare = function (event, model) {
    console.log("Would like to declare", model.chain.name);
    fsm.chainClicked(model.chain);
}


function Stock(obj) {
    this.name = obj.name;
    this.available = obj.available;
    this.count = obj.count;
    this.size = obj.size;
    this.swatch = this.name + " swatch";
    this.safe = this.size >= 11;
    this.inactive = this.size == 0;
}

Stock.prototype.getCost = function (event, model) {
    console.log("Getting chain cost from model", model);
    return app.lookupChainCost(this.name);
}

Stock.prototype.decrement = function (event, model) {
    console.log("Would like to decrement", model.stock.name);
    // fsm.chainClicked(model.chain);
    var index = app.stocksCart.map(function (stock) {
        return stock.name;
    }).indexOf(model.stock.name);

    if (index > -1) {
      app.stocksCart.splice(index, 1);
    }
}
Stock.prototype.increment = function (event, model) {
    console.log("Would like to increment", model.stock.name);
    // fsm.chainClicked(model.chain);
    app.stocksCart.push(model.stock);
    // app.stocksCart = [model.stock];
}
Stock.prototype.hasNone = function () {
    var thisName = this.name;
    return app.stocksCart.filter(function (stock) {
        return stock.name == thisName;
    }).length == 0;
}

function StockDisposer(state) {
    this.winnerChain = state.merging_chains[0];
    this.defunctChain = state.merging_chains[state.merging_chains.length - 1];
    this.state = state;
    this.disposeCart = {
        trade: 0,
        sell: 0,
    }
}

StockDisposer.prototype.tradeIncome = function () {
    return this.disposeCart.trade / 2 + " " + this.state.merging_chains[0];
}
StockDisposer.prototype.sellIncome = function () {
    return this.disposeCart.sell * app.lookupChainCost(this.defunctChain);
}
StockDisposer.prototype.keepCount = function () {
    return app.player.stocks[this.defunctChain] - this.disposeCart.trade - this.disposeCart.sell;
}
StockDisposer.prototype.canTrade = function () {
    return this.keepCount() >= 2 && fsm.acquire.supply.stocks[this.winnerChain] > this.disposeCart.trade / 2;
}
StockDisposer.prototype.canSell = function () {
    return this.keepCount() > 0;
}
StockDisposer.prototype.tradeIncrement = function (event, model) {
    model.app.stockDisposer.disposeCart.trade += 2;
}
StockDisposer.prototype.tradeDecrement = function (event, model) {
    model.app.stockDisposer.disposeCart.trade -= 2;
}
StockDisposer.prototype.sellIncrement = function (event, model) {
    model.app.stockDisposer.disposeCart.sell += 1;
}
StockDisposer.prototype.sellDecrement = function (event, model) {
    model.app.stockDisposer.disposeCart.sell -= 1;
}
StockDisposer.prototype.validate = function (event, model) {
    fsm.disposeStock(model.app.stockDisposer.disposeCart);
}


fsm.handleNewState(initialStateJson);

rivets.formatters.historyFormatter = function(value){
  // if (value[0] == "initial_draws") {
  //     return "Initial draws"
  // }
  if (value[0] == "dispose_stock") {
      // dispose_stock,admin,Imperial,[object Object],2
      return "dispose_stock," + value[1] + "," + value[2] + ",trade:" + value[3].trade + ",sell:" + value[3].sell + ",keep:" + value[4];
  }
  return value;
}

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
