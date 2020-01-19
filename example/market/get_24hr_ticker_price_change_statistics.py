import asyncio
from binance_f import RequestClient, AsyncRequestClient
from binance_f.constant.test import *
from binance_f.base.printobject import *

# request_client = RequestClient(api_key=g_api_key, secret_key=g_secret_key)

# result = request_client.get_ticker_price_change_statistics()
# # result = request_client.get_ticker_price_change_statistics(symbol="BTCUSDT")


request_client = AsyncRequestClient(api_key=g_api_key, secret=g_secret_key)
result = asyncio.run(request_client.get_ticker_price_change_statistics())

print("======= 24hr Ticker Price Change Statistics =======")
PrintMix.print_data(result)
print("===================================================")
