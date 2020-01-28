import asyncio
import typing
import urllib.parse

from binance_f.base.printobject import *
from binance_f.constant.system import WebSocketDefine
from binance_f.exception.binanceapiexception import BinanceApiException
from binance_f.impl.restapirequestimpl import RestApiRequestImpl
from binance_f.impl.websocketconnection import WebsocketConnection
from binance_f.impl.websocketrequestimpl import WebsocketRequestImpl
from binance_f.impl.websocketwatchdog import WebSocketWatchDog
from binance_f.model import *
from binance_f.model import constant, order, position
from binance_f.model.constant import *


class ConnectionsKlass:
    def __init__(self):
        self._data: typing.Dict[str, WebsocketConnection] = {}

    def append(self, connection: WebsocketConnection):
        key = connection.request.name
        self._data[key] = connection

    def clear(self):
        self._data = {}

    def __iter__(self):
        return iter(self._data.values())

    def __getitem__(self, key) -> WebsocketConnection:
        return self._data[key]


class SubscriptionClient(object):
    def __init__(self, **kwargs):
        """
        Create the subscription client to subscribe the update from server.

        :param kwargs: The option of subscription connection.
            api_key: The public key applied from Binance.
            secret_key: The private key applied from Binance.
            uri: Set the URI for subscription.
            is_auto_connect: When the connection lost is happening on the subscription line, specify whether the client
                            reconnect to server automatically. The connection lost means:
                                Caused by network problem
                                The connection close triggered by server (happened every 24 hours)
                            No any message can be received from server within a specified time, see receive_limit_ms
            receive_limit_ms: Set the receive limit in millisecond. If no message is received within this limit time,
                            the connection will be disconnected.
            connection_delay_failure: If auto reconnect is enabled, specify the delay time before reconnect.
        """
        api_key = None
        secret_key = None
        if "api_key" in kwargs:
            api_key = kwargs["api_key"]
        if "secret_key" in kwargs:
            secret_key = kwargs["secret_key"]
        self.__api_key = api_key
        self.__secret_key = secret_key
        self.websocket_request_impl = WebsocketRequestImpl(self.__api_key)
        self.connections = ConnectionsKlass()
        # self.connections = list()
        self.uri = WebSocketDefine.Uri
        is_auto_connect = True
        receive_limit_ms = 60000
        connection_delay_failure = 15
        if "uri" in kwargs:
            self.uri = kwargs["uri"]
        if "is_auto_connect" in kwargs:
            is_auto_connect = kwargs["is_auto_connect"]
        if "receive_limit_ms" in kwargs:
            receive_limit_ms = kwargs["receive_limit_ms"]
        if "connection_delay_failure" in kwargs:
            connection_delay_failure = kwargs["connection_delay_failure"]
        self.__watch_dog = WebSocketWatchDog(
            is_auto_connect, receive_limit_ms, connection_delay_failure
        )

    def thread_safe_shutdown(self, key: str, callback=None):
        connection: WebsocketConnection = self.connections[key]
        try:
            connection.thread_safe(callback=callback)
        except Exception:
            connection.shutdown_gracefully()

    def __create_connection(self, request, running_callback=None):
        connection = WebsocketConnection(
            self.__api_key, self.__secret_key, self.uri, self.__watch_dog, request
        )
        self.connections.append(connection)
        connection.connect()
        self.thread_safe_shutdown(request.name, callback=running_callback)

    def unsubscribe_all(self):
        for conn in self.connections:
            conn.close()
        self.connections.clear()

    def subscribe_aggregate_trade_event(
        self, symbol: "str", callback, error_handler=None
    ):
        """
        Aggregate Trade Streams

        The Aggregate Trade Streams push trade information that is aggregated for a single taker order every 100 milliseconds.

        Stream Name: <symbol>@aggTrade
        """
        request = self.websocket_request_impl.subscribe_aggregate_trade_event(
            symbol, callback, error_handler
        )
        request.name = "subscribe_aggregate_trade_event"
        self.__create_connection(request)

    def subscribe_mark_price_event(
        self, symbol: "str", callback, error_handler=None, running_callback=None
    ):
        """
        Mark Price Stream

        Mark price for a single symbol pushed every 3 secends.

        Stream Name: <symbol>@markPrice
        """
        request = self.websocket_request_impl.subscribe_mark_price_event(
            symbol, callback, error_handler
        )
        request.name = "subscribe_mark_price_event"
        self.__create_connection(request, running_callback=running_callback)

    def subscribe_candlestick_event(
        self,
        symbol: "str",
        interval: "CandlestickInterval",
        callback,
        error_handler=None,
    ):
        """
        Kline/Candlestick Streams

        The Kline/Candlestick Stream push updates to the current klines/candlestick every 250 milliseconds (if existing).

        Stream Name: <symbol>@kline_<interval>
        """
        request = self.websocket_request_impl.subscribe_candlestick_event(
            symbol, interval, callback, error_handler
        )
        request.name = "subscribe_candlestick_event"
        self.__create_connection(request)

    def subscribe_symbol_miniticker_event(
        self, symbol: "str", callback, error_handler=None
    ):
        """
        Individual Symbol Mini Ticker Stream

        24hr rolling window mini-ticker statistics for a single symbol pushed every 3 seconds. These are NOT the statistics of the UTC day, 
        but a 24hr rolling window from requestTime to 24hrs before.

        Stream Name: <symbol>@miniTicker
        """
        request = self.websocket_request_impl.subscribe_symbol_miniticker_event(
            symbol, callback, error_handler
        )
        request.name = "subscribe_symbol_miniticker_event"
        self.__create_connection(request)

    def subscribe_all_miniticker_event(self, callback, error_handler=None):
        """
        All Market Mini Tickers Stream

        24hr rolling window mini-ticker statistics for all symbols pushed every 3 seconds. 
        These are NOT the statistics of the UTC day, but a 24hr rolling window from requestTime to 24hrs before. 
        Note that only tickers that have changed will be present in the array.

        Stream Name: !miniTicker@arr
        """
        request = self.websocket_request_impl.subscribe_all_miniticker_event(
            callback, error_handler
        )
        request.name = "subscribe_all_miniticker_event"
        self.__create_connection(request)

    def subscribe_symbol_ticker_event(
        self, symbol: "str", callback, error_handler=None
    ):
        """
        Individual Symbol Ticker Streams

        24hr rollwing window ticker statistics for a single symbol pushed every 3 seconds. These are NOT the statistics of the UTC day, 
        but a 24hr rolling window from requestTime to 24hrs before.

        Stream Name: <symbol>@ticker
        """
        request = self.websocket_request_impl.subscribe_symbol_ticker_event(
            symbol, callback, error_handler
        )
        request.name = "subscribe_symbol_ticker_event"
        self.__create_connection(request)

    def subscribe_all_ticker_event(self, callback, error_handler=None):
        """
        All Market Tickers Stream

        24hr rollwing window ticker statistics for all symbols pushed every 3 seconds. These are NOT the statistics of the UTC day, but a 24hr rolling window from requestTime to 24hrs before. 
        Note that only tickers that have changed will be present in the array.

        Stream Name: !ticker@arr
        """
        request = self.websocket_request_impl.subscribe_all_ticker_event(
            callback, error_handler
        )
        request.name = "subscribe_all_ticker_event"
        self.__create_connection(request)

    def subscribe_symbol_bookticker_event(
        self, symbol: "str", callback, error_handler=None
    ):
        """
        Individual Symbol Book Ticker Streams

        Pushes any update to the best bid or ask's price or quantity in real-time for a specified symbol.

        Stream Name: <symbol>@bookTicker
        """
        request = self.websocket_request_impl.subscribe_symbol_bookticker_event(
            symbol, callback, error_handler
        )
        request.name = "subscribe_symbol_bookticker_event"
        self.__create_connection(request)

    def subscribe_all_bookticker_event(self, callback, error_handler=None):
        """
        All Book Tickers Stream

        Pushes any update to the best bid or ask's price or quantity in real-time for all symbols.

        Stream Name: !bookTicker
        """
        request = self.websocket_request_impl.subscribe_all_bookticker_event(
            callback, error_handler
        )
        request.name = "subscribe_all_bookticker_event"
        self.__create_connection(request)

    def subscribe_symbol_liquidation_event(
        self, symbol: "str", callback, error_handler=None
    ):
        """
        Liquidation Order Streams

        The Liquidation Order Streams push force liquidation order information for specific symbol

        Stream Name:  <symbol>@forceOrder
        """
        request = self.websocket_request_impl.subscribe_symbol_liquidation_event(
            symbol, callback, error_handler
        )
        request.name = "subscribe_symbol_liquidation_event"
        self.__create_connection(request)

    def subscribe_all_liquidation_event(self, callback, error_handler=None):
        """
        All Market Liquidation Order Streams

        The All Liquidation Order Streams push force liquidation order information for all symbols in the market.

        Stream Name: !forceOrder@arr
        """
        request = self.websocket_request_impl.subscribe_all_liquidation_event(
            callback, error_handler
        )
        request.name = "subscribe_all_liquidation_event"
        self.__create_connection(request)

    def subscribe_book_depth_event(
        self,
        symbol: "str",
        limit: "int",
        callback,
        error_handler=None,
        update_time: "UpdateTime" = UpdateTime.INVALID,
    ):
        """
        Partial Book Depth Streams

        Top bids and asks, Valid are 5, 10, or 20.

        Stream Names: <symbol>@depth<levels> OR <symbol>@depth<levels>@100ms.
        """
        print(update_time)
        request = self.websocket_request_impl.subscribe_book_depth_event(
            symbol, limit, update_time, callback, error_handler
        )
        request.name = "subscribe_book_depth_event"
        self.__create_connection(request)

    def subscribe_diff_depth_event(
        self,
        symbol: "str",
        callback,
        error_handler=None,
        update_time: "UpdateTime" = UpdateTime.INVALID,
    ):
        """
        Diff. Depth Stream

        Bids and asks, pushed every 250 milliseconds or 100 milliseconds(if existing)

        Stream Name: <symbol>@depth OR <symbol>@depth@100ms
        """
        request = self.websocket_request_impl.subscribe_diff_depth_event(
            symbol, update_time, callback, error_handler
        )
        request.name = "subscribe_diff_depth_event"
        self.__create_connection(request)

    def subscribe_user_data_event(
        self, listenKey: "str", callback, error_handler=None, running_callback=None
    ):
        """
        User Data Streams
        """
        request = self.websocket_request_impl.subscribe_user_data_event(
            listenKey, callback, error_handler
        )
        request.name = "subscribe_user_data_event"
        self.__create_connection(request, running_callback=running_callback)


class HelperMixin:
    async def _limit(self, price, quantity, kind="sell") -> order.Order:
        buy_symbol = getattr(self, "buy_symbol")
        places = getattr(self, "places")
        price_places = getattr(self, "price_places")
        client = getattr(self, "client")
        kwargs = dict(
            symbol=buy_symbol,
            side=constant.OrderSide.SELL,
            ordertype=constant.OrderType.LIMIT,
            quantity=format(places % quantity),
            price=format(price_places % price),
            timeInForce=constant.TimeInForce.GTC,
        )
        if kind == "buy":
            kwargs["side"] = constant.OrderSide.BUY
        return await client.post_order(**kwargs)

    async def _stop_limit(
        self,
        quantity,
        price,
        orderType,
        kind="long",
        reduceOnly=None,
        timeInForce=constant.TimeInForce.GTC,
    ) -> order.Order:
        buy_symbol = getattr(self, "buy_symbol")
        places = getattr(self, "places")
        price_places = getattr(self, "price_places")
        client = getattr(self, "client")
        kwargs = {
            "symbol": buy_symbol,
            "ordertype": orderType,
            "timeInForce": "GTC",
            "quantity": format(places % quantity),
            "price": format(price_places % price),
            "side": constant.OrderSide.SELL,
            "stopPrice": format(price_places % (price + 1)),
            "reduceOnly": reduceOnly,
            "timeInForce": timeInForce,
            # "workingType": constant.WorkingType.MARK_PRICE if kind=="long" else constant.WorkingType.CONTRACT_PRICE,
        }
        if kind == "short":
            kwargs["ordertype"] = orderType
            kwargs["side"] = constant.OrderSide.BUY
            kwargs["stopPrice"] = format(price_places % (price - 1))
        return await client.post_order(**kwargs)

    async def get_price(self) -> typing.Optional[float]:
        mark_price = getattr(self, "mark_price")
        buy_symbol = getattr(self, "buy_symbol")
        client = getattr(self, "client")
        if mark_price:
            result = await client.get_mark_price(symbol=buy_symbol)
            return result.markPrice
        result = await client.get_symbol_price_ticker()
        result = [x.price for x in result if x.symbol == buy_symbol]
        if result:
            return result[0]
        return None

    async def cancel_all_orders(self):
        buy_symbol = getattr(self, "buy_symbol")
        client = getattr(self, "client")
        try:
            await client.cancel_all_orders(buy_symbol)
        except BinanceApiException as e:
            pass

    async def create_limit_buy(self, price, quantity) -> order.Order:
        return await self._limit(price, quantity, kind="buy")

    async def create_limit_sell(self, price, quantity) -> order.Order:
        return await self._limit(price, quantity, kind="sell")

    async def create_stop_loss(self, price, kind, quantity=None, reduceOnly=None):
        """
        when creating stop loss, the sell price is the price used for short position
        and the buy price is the price used for long position"""
        budget = getattr(self, "budget")
        _v = quantity or budget
        return await self._stop_limit(
            _v, price, constant.OrderType.STOP, kind=kind, reduceOnly=reduceOnly
        )

    async def get_leverage(self, entry=False) -> float:
        client = getattr(self, "client")
        buy_symbol = getattr(self, "buy_symbol")
        result = await client.get_position()
        data = [x for x in result if x.symbol == buy_symbol]
        if data:
            if entry:
                return data[0].leverage, data[0].entryPrice
            return data[0].leverage

    async def get_balance(self):
        client = getattr(self, "client")
        balances = await client.get_balance()
        return {x.asset: x.balance for x in balances}

    async def update_position_margin(self, amount):
        client = getattr(self, "client")
        buy_symbol = getattr(self, "buy_symbol")
        try:
            await client.change_position_margin(
                symbol=buy_symbol.upper(), amount=amount, type=1
            )
        except Exception as e:
            print(e)

    async def update_position(self, useCurrent=True):
        interval = getattr(self, "no_of_trades", 4)
        position = await self._get_position()
        if position.entryPrice:
            currentPrice = position.entryPrice
            quantity = abs(position.positionAmt)
            kind = position.kind
        else:
            quantity = getattr(self, "quantity")
            get_price = getattr(self, "get_price")
            currentPrice = await get_price()
            kind = "short"

        return await self.create_bulk_trades(
            entry_price=currentPrice,
            leverage=position.leverage,
            quantity=quantity,
            kind=kind,
            useCurrent=useCurrent,
            take_profit_interval=interval,
        )

    async def create_bulk_trades(
        self,
        take_profit_interval=4,
        entry_price=None,
        leverage=None,
        quantity=None,
        kind=None,
        useCurrent=True
        # price_difference=50, quantity=0.5
    ):
        get_price = getattr(self, "get_price")
        take_profit_p = getattr(self, "take_profit_p")
        currentPrice = await get_price()
        trades = await self.place_bulk_orders(
            # price_difference, quantity, take_profit_p * 100, currentPrice
            currentPrice=currentPrice,
            take_profit_interval=take_profit_interval,
            entry_price=entry_price,
            leverage=leverage,
            quantity=quantity,
            kind=kind,
            useCurrent=useCurrent,
        )
        position = await self._get_position()
        await self.cancel_all_orders()
        await asyncio.gather(
            *[self.create_limit_buy(x["price"], x["quantity"]) for x in trades["buys"]]
        )
        await asyncio.gather(
            *[
                self.create_limit_sell(x["price"], x["quantity"])
                for x in trades["sells"]
            ]
        )
        if position:
            initial_margin = await self.determine_initial_margin()
            if (
                position.isolatedMargin + abs(position.unrealizedProfit)
            ) < initial_margin:
                difference = (
                    initial_margin
                    - position.isolatedMargin
                    + abs(position.unrealizedProfit)
                )

                await self.update_position_margin(difference)

    async def place_bulk_orders(
        # self, price_difference=50, quantity=0.5, percentProfit=100, currentPrice=None
        self,
        entry_price=None,
        leverage=None,
        quantity=None,
        take_profit_interval=None,
        kind=None,
        currentPrice=None,
        useCurrent=True,
    ):
        _currentPrice = currentPrice
        _take_profit_interval = take_profit_interval or getattr(self, "no_of_trades", 4)
        position = getattr(self, "position")
        get_position = getattr(self, "get_position")
        take_profit_p = getattr(self, "take_profit_p")
        maximum_quantity = getattr(self, "maximum_quantity", 5)
        multiplier = getattr(self, "slow_market_multiplier", 1)
        _kind = kind
        _leverage = leverage
        _entry_price = entry_price
        _quantity = quantity
        if not all([_kind, _leverage, _entry_price, _quantity]):
            if not position:
                position = await get_position()
                _entry_price = position.entryPrice
                _kind = position.kind
                _quantity = abs(position.positionAmt)
                _leverage = position.leverage

        if useCurrent:
            if _currentPrice:
                if _entry_price > currentPrice:
                    _currentPrice = _entry_price
                    _entry_price = currentPrice
        result = determine_profit_qty_and_price(
            take_profit_p,
            _entry_price,
            _leverage,
            _quantity,
            _take_profit_interval,
            _take_profit_interval * multiplier,
            maximum_quantity,
            _kind,
        )
        # import pdb; pdb.set_trace()
        # prices = await self.get_exit_price(
        #     abs(position.positionAmt),
        #     percentProfit,
        #     position.entryPrice,
        #     position.leverage,
        # )
        # if position.kind == "long":
        #     exitPrice = prices["bull"] - position.entryPrice
        # else:
        #     exitPrice = position.entryPrice - prices["bear"]
        # result = trade_generator(
        #     position.entryPrice,
        #     abs(position.positionAmt),
        #     maximumQuantity=maximum_quantity,
        #     quantity=quantity,
        #     entryDifference=exitPrice,
        #     kind=position.kind,
        # )
        if _currentPrice:
            bigger = _entry_price if _entry_price > _currentPrice else _currentPrice
            if _kind == "long":
                return {
                    "buys": [x for x in result["buys"] if x["price"] < _currentPrice],
                    "sells": [x for x in result["sells"] if x["price"] > bigger],
                }
            return {
                "buys": [x for x in result["buys"] if x["price"] < _currentPrice],
                "sells": [x for x in result["sells"] if x["price"] > bigger],
            }
        return result

    async def get_exit_price(
        self, quantity, percentage, entry_price=None, leverage=None
    ):
        _leverage = leverage
        _entry_price = entry_price
        if not _leverage:
            position = getattr(self, "position")
            if not position:
                get_position = getattr(self, "get_position")
                position = await get_position()
                _entry_price = position.entryPrice
            _leverage = position.leverage
        _position = determine_price(percentage / 100, _entry_price, _leverage, quantity)
        return _position
        # margin_amount = quantity * _entry_price / leverage
        # return margin_amount * _leverage / quantity

    async def get_profit_quantity(self, exit_price, pnl_quantity=None, leverage=None):
        profit_amount = pnl_quantity
        if not profit_amount:
            profit_amount = getattr(self, "profit_amount")
        _leverage = leverage
        if not _leverage:
            position = getattr(self, "position")
            if not position:
                get_position = getattr(self, "get_position")
                position = await get_position()
            _leverage = position.leverage
        return profit_amount * _leverage / exit_price

    async def take_interval_profit(self, exit_price, pnl_quantity=None):
        quantity = await self.get_profit_quantity(exit_price, pnl_quantity)
        create_take_profit = getattr(self, "create_take_profit")
        position = getattr(self, "position")
        price_check = None
        if position.kind == "long":
            if exit_price > position.entryPrice:
                price_check = True
        if position.kind == "short":
            if exit_price < position.entryPrice:
                price_check = True
        if quantity < abs(position.positionAmt) and price_check:
            return await create_take_profit(
                exit_price, position.kind, quantity=quantity
            )

    async def increase_position(self, new_entry_price, pnl_quantity=None):
        quantity = await self.get_profit_quantity(new_entry_price, pnl_quantity)
        maximum_quantity = getattr(self, "maximum_quantity", 5)
        create_take_profit = getattr(self, "create_take_profit")
        position = getattr(self, "position")
        if abs(position.positionAmt) < maximum_quantity:
            if position.positionAmt < 0.5 * maximum_quantity:
                quantity = quantity * 2
            if position.kind == "short":
                return await self.create_limit_sell(new_entry_price, quantity=quantity)
            else:
                return await self.create_limit_buy(new_entry_price, quantity=quantity)

    async def get_liquidation_price(self, wallet_balance=None, quantity=None):
        position = getattr(self, "position")
        market = getattr(self, "market")
        get_position = getattr(self, "get_position")
        _balance = wallet_balance
        _quantity = quantity
        if not position:
            position = await get_position()
        if not _quantity:
            _quantity = abs(position.positionAmt)
        if not _balance:
            _balance = position.isolatedMargin
            if position.unrealizedProfit > 0:
                _balance -= position.unrealizedProfit
            else:
                _balance += position.unrealizedProfit
        print(
            {
                "balance": _balance,
                "entry": position.entryPrice,
                "quantity": _quantity,
                "kind": position.kind,
                "pnl": position.unrealizedProfit,
            }
        )
        return liquidation(
            _balance,
            position.entryPrice,
            _quantity,
            position.kind,
            pnl=-(position.unrealizedProfit),
        )

    async def get_largest_order_price(self, kind=None):
        _kind = kind
        get_orders = getattr(self, "get_orders")
        await get_orders("open")
        trades = getattr(self, "trades")
        if not _kind:
            position = await self._get_position()
            _kind = position.kind
        print("kind is ", _kind)
        if _kind == "long":
            result = min([x.price for x in trades["open"]])
        else:
            result = max([x.price for x in trades["open"]])
        return result

    async def _get_position(self):
        position = getattr(self, "position")
        get_position = getattr(self, "get_position")
        if not position:
            position = await get_position(True)
        return position

    async def determine_initial_margin(
        self, addition=500, entry=None, kind=None, pnl=0, quantity=None
    ):
        _entry = entry
        _quantity = quantity
        _kind = kind
        if not entry or not quantity:
            position = await self._get_position()
            _entry = position.entryPrice
            _kind = position.kind
            _quantity = abs(position.positionAmt)
        max_min_price = await self.get_largest_order_price(kind=_kind)
        if _kind == "long":
            liquidation_price = max_min_price - addition
        else:
            liquidation_price = max_min_price + addition
        return wallet_balance(liquidation_price, _entry, _quantity, _kind, pnl)

    async def determine_price_info(
        self, percent, entry=None, quantity=None, leverage=None
    ):
        budget = getattr(self, "budget")
        q = quantity or budget
        print(q)
        l = leverage
        e = entry
        if not entry:
            _, e = await self.get_leverage(True)
        if not leverage:
            l, _ = await self.get_leverage(True)
        return determine_price(percent, e, l, quantity=q)


def determine_price(percent, entry, leverage, quantity=1):
    #
    # (result-entry)*quantity = pnl
    # position = pnl/percent
    dollar_value = entry / leverage
    position = dollar_value * quantity
    difference = (position * percent) / quantity
    positive = difference + entry
    negative = entry - difference
    return {
        "bull": positive,
        "bear": negative,
        "position": position,
        "net-loss": position * percent,
    }


def liquidation(balance, entry, quantity, kind="long", pnl=0, leverage=1):
    direction = 1 if kind == "long" else -1
    _position = position(entry, quantity, kind, leverage)
    maintanance_rate, maintanance_amount, maintanance_margin = get_maintanance_amount(
        _position
    )
    return (balance - maintanance_margin + pnl + (maintanance_rate - _position)) / (
        quantity * (maintanance_rate - direction)
    )


def position(entry, quantity, kind="long", leverage=1):
    direction = {"long": 1, "short": -1}
    return direction[kind] * quantity * (entry / leverage)


def get_maintanance_amount(_position):
    margin = lambda x: x * _position / 100

    if _position < 50000:
        return 0.4 / 100, 0.4 * _position / 100, margin(0.4)
    if 50000 < _position < 250000:
        return 0.5 / 100, (_position * (0.5 - 0.4) / 100) + 50, margin(0.5)
    if 250000 < _position < 1000000:
        return 1 / 100, (_position * (1 - 0.5) / 100) + 1300, margin(1)
    if 1000000 < _position < 5000000:
        return 2.5 / 100, (_position * (2.5 - 1) / 100) + 16300, margin(2.5)


def yielder(
    start_price,
    maximumQuantity,
    profit_difference=100,
    difference=50,
    quantity=0.5,
    kind="long",
):
    remaining = maximumQuantity
    starting_price = start_price
    while remaining > 0:
        large = starting_price + difference
        small = starting_price - difference
        remaining -= quantity
        yield {"high": large, "low": small}
        if kind == "long":
            starting_price = large
        else:
            starting_price = small


def trade_generator(
    entryPrice,
    currentSize,
    maximumQuantity=5,
    price_difference=50,
    quantity=0.5,
    entryDifference=100,
    kind="long",
):
    price_to_be_used_to_generate = maximumQuantity - currentSize
    maximum_trade_count = int(price_difference / quantity)
    trades = {"buys": [], "sells": []}
    if kind == "long":
        exitPrice = entryPrice + entryDifference
        trades["sells"].append(
            {"price": exitPrice, "quantity": currentSize,}
        )
    else:
        exitPrice = entryPrice - entryDifference
        trades["buys"].append(
            {"price": exitPrice, "quantity": currentSize,}
        )
    for trade in yielder(
        entryPrice,
        price_to_be_used_to_generate,
        profit_difference=entryDifference,
        difference=price_difference,
        quantity=quantity,
        kind=kind,
    ):
        if kind == "short" and trade["low"] in [entryPrice, exitPrice]:
            pass
        else:
            trades["buys"].append({"price": trade["low"], "quantity": quantity})
        if kind == "long" and trade["high"] in [exitPrice, entryPrice]:
            pass
        else:
            trades["sells"].append(
                {"price": trade["high"], "quantity": quantity,}
            )
    return trades


def get_quantity(margin_price, exit_price, leverage=1):
    return margin_price * leverage / exit_price


def exit_price_determiner(
    percent, quantity, leverage, entry_price, initial_pnl, kind="long"
):

    remaining_quantity = quantity
    start_entry = entry_price
    start_result = determine_price(percent, entry_price, leverage, quantity)
    if kind == "long":
        start_quantity = get_quantity(
            initial_pnl, start_result["bull"], leverage=leverage
        )
    else:
        start_quantity = get_quantity(
            initial_pnl, start_result["bear"], leverage=leverage
        )
    while remaining_quantity > 0.005:
        result = determine_price(percent, start_entry, leverage, start_quantity)
        profit_margin = result["position"]
        if kind == "long":
            start_entry = result["bull"]
        else:
            start_entry = result["bear"]
        yield {"price": start_entry, "quantity": start_quantity}
        _quantity = get_quantity(profit_margin, start_entry, leverage=leverage)
        start_quantity = _quantity
        remaining_quantity -= start_quantity


def initial_margin(entry_price, quantity, leverage=1):
    return (entry_price * quantity) / leverage


def determine_profit_qty_and_price(
    exit_percent,
    entry_price,
    leverage=100,
    quantity=1,
    take_profit_interval=4,
    slow_market_interval=4,
    maxQuantity=5,
    kind="long",
):
    _initial_margin = initial_margin(entry_price, quantity, leverage=leverage)
    profit_margin = _initial_margin / take_profit_interval
    if kind == "long":
        buy_interval = take_profit_interval
        sell_interval = slow_market_interval
    else:
        buy_interval = slow_market_interval
        sell_interval = take_profit_interval
    buys = [
        x
        for x in exit_price_determiner(
            exit_percent / buy_interval,
            quantity,
            leverage,
            entry_price,
            _initial_margin / buy_interval,
            kind="long",
        )
    ]
    sells = [
        x
        for x in exit_price_determiner(
            exit_percent / sell_interval,
            quantity,
            leverage,
            entry_price,
            _initial_margin / sell_interval,
            kind="short",
        )
    ]
    reverse = "short" if kind == "long" else "long"
    new_buys = []
    new_sells = []
    addition = quantity
    if kind == "long":
        new_sells = buys
        for j in sells:
            if addition < maxQuantity:
                new_buys.append(j)
                addition += j["quantity"]
    else:
        new_buys = sells
        for j in buys:
            if addition < maxQuantity:
                new_sells.append(j)
                addition += j["quantity"]
    return {"buys": new_buys, "sells": new_sells}


def wallet_balance(liquidation_price, entry, quantity, kind="long", pnl=0):
    direction = 1 if kind == "long" else -1
    _position = position(entry, quantity, kind)
    maintanance_rate, maintanance_amount, maintanance_margin = get_maintanance_amount(
        _position
    )
    top = liquidation_price * (quantity * (maintanance_rate - direction))
    balance = top - pnl - (maintanance_rate - _position) + maintanance_margin
    return balance
