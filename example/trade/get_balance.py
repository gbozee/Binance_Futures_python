from timeit import default_timer
from datetime import timedelta
import asyncio
# from binance_f import RequestClient

from binance_f import AsyncRequestClient as RequestClient
from binance_f.constant.test import *
from binance_f.base.printobject import *
from binance_f.model.constant import *

request_client = RequestClient(api_key=g_api_key, secret_key=g_secret_key)
start = default_timer()
# result = request_client.get_balance()
result = asyncio.run(request_client.get_balance())
import ipdb; ipdb.set_trace()
end = default_timer()
PrintMix.print_data(result)

print(timedelta(seconds=end - start))

