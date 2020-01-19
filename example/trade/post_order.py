from binance_f import RequestClient
from binance_f.constant.test import *
from binance_f.base.printobject import *
from binance_f.model.constant import *

request_client = RequestClient(api_key=g_api_key, secret_key=g_secret_key)
# result = request_client.post_order(
#     symbol="BTCUSDT",
#     side=OrderSide.SELL,
#     ordertype=OrderType.LIMIT,
#     timeInForce="GTC",
#     quantity=0.001,
#     price=8000.1,
# )

# PrintBasic.print_obj(result)


def limit_buy(quantity, price):
    result = request_client.post_order(
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        ordertype=OrderType.LIMIT,
        timeInForce="GTC",
        quantity=quantity,
        price=float("%.1f" % price),
    )
    PrintBasic.print_obj(result)


def limit_sell(quantity, price):
    result = request_client.post_order(
        symbol="BTCUSDT",
        side=OrderSide.SELL,
        ordertype=OrderType.LIMIT,
        timeInForce="GTC",
        quantity=quantity,
        price=float("%.1f" % price),
    )
    PrintBasic.print_obj(result)


def get_price(symbol):
    markets = request_client.get_symbol_price_ticker()
    result = [x.price for x in markets if x.symbol == symbol.upper()]
    if result:
        return float(result[0])


def stop_limit(quantity, price, orderType, kind="long"):
    kwargs = {
        "symbol": "BTCUSDT",
        "ordertype": orderType,
        "timeInForce": "GTC",
        "quantity": quantity,
        "price": float("%.1f" % price),
        "side": OrderSide.SELL,
        "stopPrice": price + 1,
        "workingType": WorkingType.MARK_PRICE,
    }
    if kind == "short":
        kwargs["ordertype"] = orderType
        kwargs["side"] = OrderSide.BUY
    result = request_client.post_order(**kwargs)
    PrintBasic.print_obj(result)


def take_profit(quantity, price, kind="long"):
    stop_limit(quantity, price, OrderType.TAKE_PROFIT, kind=kind)


def stop_loss(quantity, price, kind="long"):
    stop_limit(quantity, price, OrderType.STOP, kind=kind)


def cancel_order(self, orderId):
    request_client.cancel_order(symbol="BTCUSDT", orderId=orderId)


def cancel_all_orders(self):
    request_client.cancel_all_orders(symbol="BTCUSDT")


# limit_sell(0.002,8639)
# take_profit(0.001, 8600, kind="short")
stop_loss(0.002, 8639, kind="short")  # if no trade,

