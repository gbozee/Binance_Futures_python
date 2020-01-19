import asyncio
from binance_f import AsyncRequestClient as RequestClient
from binance_f.constant.test import *
from binance_f.base.printobject import *

request_client = RequestClient(api_key=g_api_key, secret_key=g_secret_key)

result = asyncio.run(request_client.get_servertime())

print("server time: ", result)
