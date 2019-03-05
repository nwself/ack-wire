function StagedStockModel(attributes) {
  this.data = attributes; // attributes should include chain: "Worldwide" model???

  this.increment = function (event, scope) {
    // something like this???
    scope.data.chain.stagedCount++;
  }
}

function registerStagingStock() {
  rivets.components['staged-stock'] = {
      template: function() {
          return '<button rv-on-click="increment">+</button>' +
              '<button rv-on-click="decrement">-</button>' +
              '<button rv-on-click="toggleColor">toggle color</button>';
      },
      initialize: function(el, attributes) {
          return new StagedStockModel(attributes);
      }
  };
}
