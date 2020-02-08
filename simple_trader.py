import asyncio
import functools
import logging
import os
import typing
import json

import binance_f
from binance_f.model import constant, order, orderupdate, position
from binance_f.subscriptionclient import HelperMixin
from binance_f.exception.binanceapiexception import BinanceApiException
from bot import ThreadLogic
from socket_client import ServerSocketManager
from websocket import create_connection

logger = logging.getLogger("binance-futures")
logger.setLevel(level=logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(pathname)s - %(lineno)d - %(message)s"
    )
)
logger.addHandler(handler)


class BotController:
    def __init__(
        self,
        api_key,
        api_secret,
        interval=10,
        url="ws://backup.tuteria.com:5020/",
        **kwargs,
    ):
        self.sub_client = binance_f.SubscriptionClient(
            api_key=api_key, secret_key=api_secret, debug=True
        )
        self.client = binance_f.RequestClient(
            api_key=api_key, secret_key=api_secret, debug=False
        )
        self.params = dict(api_key=api_key, api_secret=api_secret, **kwargs)
        self.last_action = None
        self.listen_key = self.client.start_user_data_stream()
        self.counter = 0
        self.interval = interval
        self.url = url
        self.thread_logic = ThreadLogic()

    @property
    def helper(self):
        return TradeHelper(**self.params)

    def notify_controller(self, data):
        ws = create_connection(self.url + "config")
        ws.send(json.dumps(data))
        ws.close()

    def callback(
        self, data_type: "SubscribeMessageType", event: orderupdate.OrderUpdate
    ):
        if data_type == constant.SubscribeMessageType.RESPONSE:
            logger.info("Event ID: %s" % event)
            # self.notify_controller({"action": "update_trade_price"})
        elif data_type == constant.SubscribeMessageType.PAYLOAD:
            if event.eventType == "ORDER_TRADE_UPDATE":
                if event.orderStatus in ["FILLED"]:
                    self.notify_controller(
                        {"action": "trade_completed", "price": event.price}
                    )
                logger.info(event.__dict__)
                if event.orderStatus == "CANCELED":
                    self.notify_controller({"action": "cancelled"})

            elif event.eventType == "listenKeyExpired":
                logger.info("Event: %s" % event.eventType)
                logger.info("Event time: %s" % event.eventTime)
                logger.info("CAUTION: YOUR LISTEN-KEY HAS BEEN EXPIRED!!!")
                logger.info("CAUTION: YOUR LISTEN-KEY HAS BEEN EXPIRED!!!")
                logger.info("CAUTION: YOUR LISTEN-KEY HAS BEEN EXPIRED!!!")

        else:
            logger.info("Unknown Data:")
        # logger.info()

    def error(self, e: "BinanceApiException"):
        logger.info(e.error_code + e.error_message)

    @property
    def queue(self):
        return self.thread_logic.queue

    def running_callback(self):
        self.counter += self.interval
        logger.info("Counter current count %s" % self.counter)
        time.sleep(1 * self.interval)
        # while not self.queue.empty():
        #     item = self.queue.get()
        #     self.notify_controller(item)

        time.sleep(1 * self.interval)
        if self.counter == 60 * 50:
            logger.info("Update listen_key after 50 minutes")
            self.client.keep_user_data_stream()
            self.counter = 0

    def start_account_servers(self, loop, **kwargs):
        self.event_loop = loop
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.start_server_socket(loop, self.thread_logic.queue))
        loop.run_forever()

    async def start_server_socket(self, loop, server_queue):
        self.manager = ServerSocketManager(url=self.url, loop=loop)
        logger.info("Application websocket server started")
        logger.info(f"url is {self.url}")
        await self.manager.start_socket("config", self.on_server_response)
        # new_server_response = functools.partial(self.on_server_response, server_queue)
        # await self.manager.start_socket("config", new_server_response)

    def start(self):
        try:
            self.thread_logic.start(self.start_account_servers, "background_thread")
            self.sub_client.subscribe_user_data_event(
                self.listen_key,
                self.callback,
                self.error,
                running_callback=self.running_callback,
            )
        except BinanceApiException as e:
            logger.info("Sleeping for 10 seconds")
            time.sleep(60 * 1)
            self.listen_key = self.client.start_user_data_stream()
            self.start()
        # self.sub_client.subscribe_mark_price_event(
        #     "btcusdt", self.callback, self.error, running_callback=self.long_callback
        # )
        while True:
            try:
                pass
            except KeyboardInterrupt:
                break
                pass
            except Exception:
                break

    async def on_server_response(self, data):
        logger.info(data)
        print(type(data))
        if (type(data)) == dict:
            action = data.get("action")
            try:
                if action == "trade_completed":
                    await self.helper.update_position(data.get("price"))
                    # await asyncio.gather(*[x.check_and_update() for x in self.helpers])
                if action == "cancelled":
                    await self.helper.check_to_recreate()
                    # await self.helper.update_position()
            except Exception as e:
                logging.info("Error occured with actions")
                logging.exception(e)

    @classmethod
    async def load_credentials(
        cls, db_url, name, names=(), market_name="btc", config=None, **additional_kwargs
    ):
        interface = db.DBInterface(url=db_url)
        _, data = await interface.load_db_data(False)
        # future_dict = await interface.get_future_data(name)
        # kwargs = future_dict["future"].get(market_name)
        # kwargs = config[market_name]
        kwargs = {}
        value = [x for x in data if x.owner in names]
        named_account = [x for x in data if x.owner == name]
        if named_account:
            return cls(
                db_url=db_url,
                account_name=name,
                accounts=[
                    dict(
                        api_key=x.api_key,
                        api_secret=x.api_secret,
                        owner=x.owner,
                        **x.future_markets[market_name],
                    )
                    for x in value
                ],
                api_key=named_account[0].api_key,
                api_secret=named_account[0].api_secret,
                **kwargs,
                **additional_kwargs,
            )


class TradeHelper(HelperMixin):
    def __init__(
        self,
        api_key: str = None,
        api_secret: str = None,
        coin="BTC",
        buy_market="USDT",
        budget=0.2,
        percent: typing.Dict[str, float] = None,
        mark_price=True,
        places="%.3f",
        price_places="%.2f",
        maximum_quantity=5,
        slow_market_multiplier=1,
        owner=None,
        **kwargs,
    ):
        self.mark_price = mark_price
        self.owner = owner
        self.maximum_quantity = maximum_quantity
        self.places = places
        self.price_places = price_places
        self.percent = percent
        if not self.percent:
            self.percent = {"stop_loss": 0.15, "take_profit": 1}
        self.coin = coin
        self.market = buy_market
        self.budget = budget
        self.client = binance_f.AsyncRequestClient(
            api_key=api_key, secret_key=api_secret, debug=True
        )
        self.trades: typing.Dict[str, typing.List[order.Order]] = {
            "open": [],
            "closed": [],
        }
        self.position = None

    @property
    def take_profit_p(self) -> float:
        if self.percent:
            return self.percent.get("take_profit") or 1
        return 1

    @property
    def stop_loss_p(self) -> float:
        if self.percent:
            return self.percent.get("stop_loss") or 0.15
        return 0.15

    @property
    def buy_symbol(self):
        return self.coin + self.market

    async def get_orders(self, side=None):
        if not side:
            result = await self.client.get_all_orders(symbol=self.buy_symbol)
            self.trades["open"] = [x for x in result if x.status == "NEW"]
            self.trades["closed"] = [x for x in result if x.status == "FILLED"]
        else:
            result = await self.client.get_open_orders()
            self.trades["open"] = result
        return result

    async def get_position(self, with_none=False) -> typing.Optional[position.Position]:
        if not self.position:
            info: typing.List[position.Position] = await self.client.get_position()
            result = [x for x in info if x.symbol == self.buy_symbol]
            if result:
                _result = result[0]
                if _result.entryPrice > 0:
                    self.position = _result
                    return _result
                if with_none:
                    return _result
            self.position = None
            logging.info("Empty position in place")
            return None
        return self.position

    async def create_take_profit(self, price, kind, quantity=None, _type="limit"):
        """take profit with sell_price for short position is a buy trade and fires immediately,
        resulting in a long position
        ======================================================================================
        for buy_price with short position, this waits the the price falls below the buyprice before placing
        ideal for entering long position
        ==================================================================================="""
        options = {
            "long": lambda x: x.side == constant.OrderSide.SELL,
            "short": lambda x: x.side == constant.OrderSide.BUY,
        }
        # if not self.trades["open"]:
        #     await self.get_orders("open")
        q = self.budget * self.take_profit_p
        _quantity = quantity or q
        # pendings = [
        #     x
        #     for x in self.trades["open"]
        #     if options[kind](x)
        #     and format(self.places % x.origQty) == format(self.places % _quantity)
        # ]
        # if not pendings:
        if _type == "market":
            return await self._stop_market(
                _quantity, price, constant.OrderType.TAKE_PROFIT_MARKET, kind=kind
            )
        return await self._stop_limit(
            _quantity, price, constant.OrderType.TAKE_PROFIT, kind=kind
        )

    async def check_to_recreate(self):
        position, orders = await asyncio.gather(
            self.get_position(True), self.get_orders("open")
        )
        if len(orders) == 0 and position:
            await self.update_position(position.entryPrice, position.leverage)

    async def update_position(self, new_entry=None, leverage=125):
        position = await self.get_position(True)
        entry_price = new_entry
        _leverage = leverage
        with_position = False
        if not new_entry and position.entryPrice:
            with_position = True
            entry_price = position.entryPrice
            _leverage = position.leverage
        if entry_price:
            half_take_profit_price = determine_price(
                self.take_profit_p / 2, entry_price, _leverage, self.budget,
            )
            full_take_profit_price = determine_price(
                self.take_profit_p, entry_price, _leverage, self.budget
            )
            tasks = []
            open_orders = await self.get_orders("open")
            condition = 0 < len(open_orders) < 5
            if with_position:
                condition = 0 < len(open_orders) < 4
            await self.cancel_all_orders()
            tasks.append(
                self.create_take_profit(
                    half_take_profit_price["bull"], "long", self.budget / 2
                ),
            )
            tasks.append(
                self.create_take_profit(
                    full_take_profit_price["bull"], "long", self.budget / 2,
                )
            )
            tasks.append(
                self.create_limit_buy(full_take_profit_price["bear"], self.budget / 2)
            )
            tasks.append(
                self.create_limit_buy(half_take_profit_price["bear"], self.budget / 2)
            )
            if not with_position:
                tasks.append(self.create_limit_buy(entry_price, self.budget))

            await asyncio.gather(*tasks)

    async def stop_loss_helper(self, entry_price, quantity, leverage, kind):
        result = await self.determine_price_info(
            self.stop_loss_p, entry_price, quantity, leverage,
        )
        if kind == "long":
            stop_price = result["bear"]
        else:
            stop_price = result["bull"]
        await self.create_stop_loss(
            stop_price, kind, quantity, workingType=WorkingType.MARK_PRICE,
        )


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


marketss = {
    "btc": {
        "coin": "BTC",
        "budget": 0.1,
        "slow_market_multiplier": 1,
        "percent": {"stop_loss": 2, "take_profit": 4},
        # "percent": {"stop_loss": 0.15, "take_profit": 3.5},
        "margin_error": 1,
        "maximum_quantity": 1,
        "no_of_trades": 3,
        "run_range": 3000,
        "trade_interval": 25,
        "margin_support": True,
        "spot_support": True,
    },
}

profit_api_key = os.getenv("PROFIT_BINANCE_API_KEY")
profit_api_secret = os.getenv("PROFIT_BINANCE_API_SECRET")
dads_api_key = os.getenv("DAD_BINANCE_API_KEY")
dads_api_secret = os.getenv("DAD_BINANCE_API_SECRET")
oye_api_key = os.getenv("OYENIYI_API_KEY")
oye_api_secret = os.getenv("OYENIYI_API_SECRET")
tmosco_api_key = os.getenv("TMOSCO_API_KEY")
tmosco_api_secret = os.getenv("TMOSCO_API_SECRET")
# helper = TradeHelper(api_key=oye_api_key, api_secret=oye_api_secret, **marketss["btc"])
# helper = TradeHelper(
#     api_key=tmosco_api_key,
#     api_secret=tmosco_api_secret,
#     owner="tmosco",
#     **marketss["btc"],
# )

helper = BotController(
    api_key=tmosco_api_key,
    api_secret=tmosco_api_secret,
    owner="tmosco",
    **marketss["btc"],
)
helper.start()


# def action_in_main_thread(action):
#     loop = asyncio.get_event_loop()
#     return loop.run_until_complete(action)


# result = action_in_main_thread(helper.update_position(9700))
# print(result)
