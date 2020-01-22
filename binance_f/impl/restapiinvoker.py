import requests
import httpx
from binance_f.exception.binanceapiexception import BinanceApiException
from binance_f.impl.utils import *
from binance_f.impl.restapirequest import RestApiRequest

# from binance_f.base.printobject import *


def check_response(json_wrapper):
    if json_wrapper.contain_key("success"):
        success = json_wrapper.get_boolean("success")
        if success is False:
            err_code = json_wrapper.get_int_or_default("code", "")
            err_msg = json_wrapper.get_string_or_default("msg", "")
            if err_code == "":
                raise BinanceApiException(
                    BinanceApiException.EXEC_ERROR, "[Executing] " + err_msg
                )
            else:
                raise BinanceApiException(
                    BinanceApiException.EXEC_ERROR,
                    "[Executing] " + str(err_code) + ": " + err_msg,
                )
    elif json_wrapper.contain_key("code"):
        code = json_wrapper.get_int("code")
        msg = json_wrapper.get_string_or_default("msg", "")
        if code != 200:
            raise BinanceApiException(
                BinanceApiException.EXEC_ERROR, "[Executing] " + str(code) + ": " + msg
            )


def call_sync(request, debug=True):
    response = None
    if request.method == "GET":
        response = requests.get(request.host + request.url, headers=request.header)
    elif request.method == "POST":
        response = requests.post(request.host + request.url, headers=request.header)
    elif request.method == "DELETE":
        response = requests.delete(request.host + request.url, headers=request.header)
    elif request.method == "PUT":
        response = requests.put(request.host + request.url, headers=request.header)
    if response:
        json_wrapper = parse_json_from_string(response.text)
        if debug:
            print(response.text)
        check_response(json_wrapper)
        return request.json_parser(json_wrapper)


async def call_async(request: RestApiRequest, debug=True):
    async with httpx.AsyncClient(base_url=request.host,timeout=20) as client:
        response = None
        if request.method == "GET":
            response = await client.get(request.url, headers=request.header)
        elif request.method == "POST":
            response = await client.post(request.url, headers=request.header)
        elif request.method == "DELETE":
            response = await client.delete(request.url, headers=request.header)
        elif request.method == "PUT":
            response = await client.put(request.url, headers=request.header)
        if response:
            json_wrapper = parse_json_from_string(response.text)
            if debug:
                print(response.text)
            check_response(json_wrapper)
            return request.json_parser(json_wrapper)

