class Position:
    def __init__(self):
        self.entryPrice = 0.0
        self.leverage = 0.0
        self.maxNotionalValue = 0.0
        self.liquidationPrice = 0.0
        self.markPrice = 0.0
        self.positionAmt = 0.0
        self.symbol = ""
        self.unrealizedProfit = 0.0
        self.marginType = ""
        self.isolatedMargin = ""
        self.fetched = False

    @property
    def kind(self) -> str:
        return "long" if self.entryPrice > self.liquidationPrice else "short"

    @staticmethod
    def json_parse(json_data):
        result = Position()
        result.leverage = json_data.get_float("leverage")
        result.maxNotionalValue = json_data.get_float("maxNotionalValue")
        result.liquidationPrice = json_data.get_float("liquidationPrice")
        result.markPrice = json_data.get_float("markPrice")
        try:
            result.entryPrice = json_data.get_float("entryPrice")
        except Exception:
            result.entryPrice = result.markPrice
        result.positionAmt = json_data.get_float("positionAmt")
        result.symbol = json_data.get_string("symbol")
        result.unrealizedProfit = json_data.get_float("unRealizedProfit")
        result.marginType = json_data.get_string("marginType")
        result.isolatedMargin = json_data.get_float("isolatedMargin")
        return result
