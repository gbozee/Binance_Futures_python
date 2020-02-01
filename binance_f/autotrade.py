def determine_position(percent, entry, leverage, quantity=1, kind="long"):
    dollar_value = entry / leverage
    position = dollar_value * quantity
    difference = (position * percent) / quantity
    positive = difference + entry
    negative = entry - difference
    if kind == "long":
        return {"trade": positive, "position": position, "profit": position * percent}
    return {"trade": negative, "position": position, "profit": position * percent}


def trade_generator(
    maximum_quantity,
    interval,
    range,
    position_size,
    take_profit=2,
    entry_price=None,
    current_price=None,
    take_profit_count=3,
    kind="long",
    leverage=125,
    stop_loss_count=2,
):
    multiplier = 1
    spread_multiplier = 1
    start = entry_price or current_price
    remaining_quantity = maximum_quantity
    minimum_trades = range / interval
    min_trade_quantity = maximum_quantity / minimum_trades
    position = 0
    if position_size > 0:
        data = determine_position(
            take_profit, entry_price, leverage, position_size, kind=kind
        )
        position = data["position"]
    xx = determine_position(
        take_profit, entry_price, leverage, maximum_quantity, kind=kind
    )
    maximum_position = xx["position"]
    trade_quantity = min_trade_quantity
    if position < (maximum_position / take_profit_count):
        trade_quantity *= 3

    def condition(v):
        if kind == "long":
            return v > ending_price
        return v < ending_price

    if position_size < (maximum_quantity / 2):
        current_price = None

    result = get_result_pair(
        entry_price=start,
        minimum_trades=minimum_trades,
        pair=take_profit_count,
        last_price=current_price,
        multiplier=multiplier,
        _range=interval,
        leverage=leverage,
        maximum_size=maximum_quantity,
        current_size=position_size,
        trade_size=trade_quantity,
        kind=kind,
        reduce_multiplier=stop_loss_count,
        spread_multiplier=spread_multiplier,
    )

    return result


class AutoTrader:
    def __init__(
        self, range=1000, maximum_quantity=6, interval=50, take_profit=2, pair=4
    ):
        """[summary]
        
        Keyword Arguments:
            range {int} -- The projected duration of the run e.g from 8600 to 9600 (default: {1000})
            maximum_quantity {int} -- The maximum number of coins that should be purchased (default: {6})
            interval {int} -- The interval between when trades should be placed (default: {50})
            take_profit {float} -- The percentage value for the expected returns (default: {2})
            pair {int} -- The number of trades to place on both sell and buy side (default: {4})
        """
        self.range = range
        self.maximum_quantity = maximum_quantity
        self.interval = interval
        self.take_profit = take_profit
        self.pair = pair
        self.stop_loss = 2

    def build_trades(self, current_price, position):
        return trade_generator(
            self.maximum_quantity,
            self.interval,
            self.range,
            abs(position.positionAmt),
            take_profit=self.take_profit,
            entry_price=position.entryPrice,
            current_price=current_price,
            take_profit_count=self.pair,
            kind=position.kind,
            leverage=position.leverage,
            stop_loss_count=self.stop_loss,
        )


def get_interval(minimum_range, reverse=False):
    start = 0
    end = minimum_range
    if reverse:
        start = -(minimum_range + 2)
        end = start + minimum_range
    return start, end


def start_params(minimum_range, reverse=False):
    start, end = get_interval(minimum_range, reverse=reverse)
    if reverse:
        counter = end
        last = start
    else:
        counter = start
        last = end
    return counter, last


def gen_prices(
    entry_price=None,
    minimum_trades=10,
    reverse=False,
    multiplier=1,
    trade_size=None,
    _range=50,
    spread_multiplier=1,
    leverage=125,
    maximum_size=3,
    current_size=0,
):
    x_multiplier = multiplier
    r_reverse = reverse
    counter, last = start_params(minimum_trades, reverse=r_reverse)
    first_price = entry_price
    first_price = float(first_price)
    range_value = _range * spread_multiplier
    default_quantity = trade_size
    position_size = current_size
    while position_size < maximum_size:
        i = counter
        # if i >= 0:
        if (first_price + ((i + 1) * range_value)) > range_value:
            price = first_price + ((i + 1) * range_value)
        else:
            range_value = range_value / 10
            price = first_price + (((i + 1) * range_value))
        if r_reverse:
            counter -= 1
        else:
            counter += 1
        # yield price
        quantity = default_quantity * x_multiplier
        rr = {
            "price": price,
            "quantity": quantity,
            "position": price * quantity / leverage,
        }
        position_size += quantity
        params = yield rr
        if params:
            if type(params) == tuple:
                first_price = params[0]
                if len(params) > 1:
                    r_reverse = params[1]
                if len(params) > 2:
                    x_multiplier = params[2]
                if len(params) > 3:
                    default_quantity = params[3]

            counter, last = start_params(minimum_trades, reverse=r_reverse)


def generate_buy_sell_pair(
    entry_price,
    minimum_trades=10,
    last_price=None,
    with_generator=False,
    multiplier=1,
    leverage=125,
    maximum_size=3,
    current_size=0,
    _range=50,
    trade_size=None,
    kind="long",
    spread_multiplier=1,
    reduce_multiplier=2,
):
    sell_generator = gen_prices(
        entry_price=entry_price,
        minimum_trades=minimum_trades,
        multiplier=multiplier,
        leverage=leverage,
        trade_size=trade_size,
        maximum_size=maximum_size,
        current_size=current_size,
        spread_multiplier=spread_multiplier,
        _range=_range,
    )
    buy_generator = gen_prices(
        entry_price=entry_price,
        minimum_trades=minimum_trades,
        multiplier=multiplier,
        leverage=leverage,
        trade_size=trade_size,
        maximum_size=maximum_size,
        current_size=current_size,
        spread_multiplier=spread_multiplier,
        _range=_range,
        reverse=True,
    )
    try:
        first_sell = sell_generator.send(None)
        first_buy = buy_generator.send(None)
        if last_price:
            first_buy = buy_generator.send((last_price, True, multiplier))
            first_sell = sell_generator.send((last_price, False, multiplier))
        bb = [first_buy]
        ss = [first_sell]
    except StopIteration as e:
        if kind == "long":
            sell_generator = gen_prices(
                entry_price=last_price,
                minimum_trades=minimum_trades,
                multiplier=multiplier,
                leverage=leverage,
                trade_size=trade_size * reduce_multiplier,
                maximum_size=maximum_size,
                current_size=0,
                spread_multiplier=spread_multiplier,
                reverse=True,
                _range=_range,
            )
        else:
            buy_generator = gen_prices(
                entry_price=last_price,
                minimum_trades=minimum_trades,
                multiplier=multiplier,
                leverage=leverage,
                trade_size=trade_size * reduce_multiplier,
                maximum_size=maximum_size,
                current_size=0,
                spread_multiplier=spread_multiplier,
                _range=_range,
                reverse=True,
            )
        bb = []
        ss = []
    if with_generator:
        return bb, ss, buy_generator, sell_generator
    return first_buy, first_sell


def get_result_pair(
    entry_price=None,
    minimum_trades=10,
    pair=2,
    last_price=None,
    multiplier=1,
    _range=None,
    spread_multiplier=1,
    leverage=125,
    maximum_size=3,
    current_size=0,
    kind="long",
    trade_size=None,
    reduce_multiplier=1,
):
    buys, sells, buy_generator, sell_generator = generate_buy_sell_pair(
        entry_price,
        minimum_trades=minimum_trades,
        last_price=last_price,
        with_generator=True,
        multiplier=multiplier,
        leverage=leverage,
        maximum_size=maximum_size,
        current_size=current_size,
        _range=_range,
        trade_size=trade_size,
        spread_multiplier=spread_multiplier,
        reduce_multiplier=reduce_multiplier,
        kind=kind,
    )
    if not buys:
        arr = []
        if kind == "long":
            v = sell_generator
        else:
            v = buy_generator
        while len(arr) < pair:
            try:
                sell = v.send(None)
                arr.append(sell)
            except StopIteration as e:
                break
        if kind == "long":
            sells = arr
            buys = []
        else:
            buys = arr
            sells = []
    else:
        while len(buys) < pair:
            try:
                buy = buy_generator.send(None)
                sell = sell_generator.send(None)
                buys.append(buy)
                sells.append(sell)
            except StopIteration as e:
                break
    q = [x["quantity"] for x in sells]
    if sells:
        sells = [
            {
                **x[0],
                # "quantity": x[1],
                # "dollar": float(f"{price_places}" % (x[0]["price"] * x[1])),
            }
            for x in zip(sells, reversed(q))
        ]
    return {
        "buys": buys,
        "sells": sells,
    }
