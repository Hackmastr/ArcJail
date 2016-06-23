APP['shop'] = function (motdPlayer) {
    var shop = this;
    var nodes = {};
    nodes['current-account'] = document.getElementById('current-account');
    nodes['items-container'] = document.getElementById('items-container');
    nodes['inventory-container'] = document.getElementById('inventory-container');
    nodes['item-stats'] = document.getElementById('item-stats');

    var currentAccount = 0;

    var renderCurrentAccount = function (accountFormatted) {
        clearNode(nodes['current-account']);
        nodes['current-account'].appendChild(document.createTextNode(accountFormatted + "c"));
    };

    var renderShopItems = function (items) {
        clearNode(nodes['items-container']);
        for (var i = 0; i < items.length; i++) {
            (function (item) {
                if ((i + 1) % 9 == 0) {
                    var div = nodes['items-container'].appendChild(document.createElement('div'));
                    div.classList.add('clear');
                }

                var itemContainer = nodes['items-container'].appendChild(document.createElement('div'));
                itemContainer.classList.add('item-container');
                itemContainer.style.backgroundImage = 'url("/static/arcjail/img/items/' + item.icon + '")';

                var priceTag = itemContainer.appendChild(document.createElement('div'));
                priceTag.classList.add('price-tag');
                priceTag.appendChild(document.createTextNode(item.price + "c"));

                var canBuy = true;

                if (item.price > currentAccount) {
                    priceTag.classList.add('too-expensive');
                    canBuy = false;
                }

                if (item['cannot_buy_reason']) {
                    itemContainer.classList.add('cannot-buy');
                    canBuy = false;
                }

                if (canBuy)
                    itemContainer.addEventListener('click', function (e) {
                        motdPlayer.post({
                            action: "buy",
                            item_id: item.id,
                        }, function (data) {
                            handleResponseData(data);
                        }, function (error) {
                            alert("Purchase error\n" + error);
                        });
                    });

                // Stats render
                itemContainer.addEventListener('mouseover', function (e) {
                    clearNode(nodes['item-stats']);
                    var span;

                    if (item['cannot_buy_reason']) {
                        span = nodes['item-stats'].appendChild(document.createElement('span'));
                        span.appendChild(document.createTextNode(item['cannot_buy_reason']));
                        span.classList.add('cannot-buy-reason');

                        nodes['item-stats'].appendChild(document.createElement('br'));
                        nodes['item-stats'].appendChild(document.createElement('br'));
                    }

                    span = nodes['item-stats'].appendChild(document.createElement('span'));
                    span.appendChild(document.createTextNode(item['caption']));
                    span.classList.add('name');

                    nodes['item-stats'].appendChild(document.createElement('br'));
                    nodes['item-stats'].appendChild(document.createElement('br'));

                    span = nodes['item-stats'].appendChild(document.createElement('span'));
                    span.appendChild(document.createTextNode(item['description']));
                    span.classList.add('description');

                    nodes['item-stats'].appendChild(document.createElement('br'));
                    nodes['item-stats'].appendChild(document.createElement('br'));

                    var li, ul = nodes['item-stats'].appendChild(document.createElement('ul'));
                    [
                        'stat_max_per_slot',
                        'stat_team_restriction',
                        'stat_manual_activation',
                        'stat_auto_activation',
                        'stat_max_sold_per_round',
                    ].forEach(function (stat, index, array) {
                        if (item[stat] == null)
                            return;

                        li = ul.appendChild(document.createElement('li'));
                        li.appendChild(document.createTextNode(item[stat]));
                    });

                    nodes['item-stats'].appendChild(document.createElement('br'));

                    span = nodes['item-stats'].appendChild(document.createElement('span'));
                    span.appendChild(document.createTextNode(item['stat_price']));
                    span.classList.add('price');

                    nodes['item-stats'].classList.add('visible');
                });

                itemContainer.addEventListener('mouseout', function (e) {
                    nodes['item-stats'].classList.remove('visible');
                });

            })(items[i]);
        }

        var div = nodes['items-container'].appendChild(document.createElement('div'));
        div.classList.add('clear');
    };

    var renderInventoryItems = function (items) {
        clearNode(nodes['inventory-container']);
        for (var i = 0; i < items.length; i++) {
            (function (item) {
                if ((i + 1) % 9 == 0) {
                    var div = nodes['inventory-container'].appendChild(document.createElement('div'));
                    div.classList.add('clear');
                }

                var itemContainer = nodes['inventory-container'].appendChild(document.createElement('div'));
                itemContainer.classList.add('item-container');
                itemContainer.style.backgroundImage = 'url("/static/arcjail/img/items/' + item.icon + '")';

                var canUse = true;

                if (item['cannot_use_reason']) {
                    itemContainer.classList.add('cannot-use');
                    canUse = false;
                }

                if (canUse)
                    itemContainer.addEventListener('click', function (e) {
                        motdPlayer.post({
                            action: "use",
                            item_id: item.id,
                        }, function (data) {
                            handleResponseData(data);
                        }, function (error) {
                            alert("Purchase error\n" + error);
                        });
                    });

                // Stats render
                itemContainer.addEventListener('mouseover', function (e) {
                    clearNode(nodes['item-stats']);
                    var span;

                    if (item['cannot_use_reason']) {
                        span = nodes['item-stats'].appendChild(document.createElement('span'));
                        span.appendChild(document.createTextNode(item['cannot_use_reason']));
                        span.classList.add('cannot-use-reason');

                        nodes['item-stats'].appendChild(document.createElement('br'));
                        nodes['item-stats'].appendChild(document.createElement('br'));
                    }

                    span = nodes['item-stats'].appendChild(document.createElement('span'));
                    span.appendChild(document.createTextNode(item['caption']));
                    span.classList.add('name');

                    nodes['item-stats'].appendChild(document.createElement('br'));
                    nodes['item-stats'].appendChild(document.createElement('br'));

                    span = nodes['item-stats'].appendChild(document.createElement('span'));
                    span.appendChild(document.createTextNode(item['description']));
                    span.classList.add('description');

                    nodes['item-stats'].appendChild(document.createElement('br'));
                    nodes['item-stats'].appendChild(document.createElement('br'));

                    var li, ul = nodes['item-stats'].appendChild(document.createElement('ul'));
                    [
                        'stat_max_per_slot',
                        'stat_team_restriction',
                        'stat_manual_activation',
                        'stat_auto_activation',
                        'stat_max_sold_per_round',
                    ].forEach(function (stat, index, array) {
                        if (item[stat] == null)
                            return;

                        li = ul.appendChild(document.createElement('li'));
                        li.appendChild(document.createTextNode(item[stat]));
                    });

                    nodes['item-stats'].appendChild(document.createElement('br'));

                    span = nodes['item-stats'].appendChild(document.createElement('span'));
                    span.appendChild(document.createTextNode(item['stat_price']));
                    span.classList.add('price');

                    nodes['item-stats'].classList.add('visible');
                });

                itemContainer.addEventListener('mouseout', function (e) {
                    nodes['item-stats'].classList.remove('visible');
                });

            })(items[i]);
        }

        var div = nodes['inventory-container'].appendChild(document.createElement('div'));
        div.classList.add('clear');
    };

    var handleResponseData = function (data) {
        currentAccount = data['account'];
        renderShopItems(data['shop_items']);
        renderInventoryItems(data['inventory_items']);
        renderCurrentAccount(data['account_formatted']);
    };

    document.addEventListener('mousemove', function(e) {
        nodes['item-stats'].style.top = e.screenY + 2 + 'px';
        nodes['item-stats'].style.left = e.screenX + 15 + 'px';
    });

    motdPlayer.retarget('json-shop', function () {
        motdPlayer.post({
            action: "update",
        }, function (data) {
            handleResponseData(data);
        }, function (error) {
            alert("Initialization error\n" + error);
        });
    }, function (error) {
        alert("Retargeting error\n" + error);
    });
}