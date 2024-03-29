# /bin/env python3
#
# pip install pyexch
#
from datetime import datetime, timezone
# from json import dump, dumps
from time import time

# from pyjson5 import load, loads

from pyexch.exchange import Exchange  # , data_toDict

MAKER = 0.006
TAKER = 0.008


def main():
    cbv3 = Exchange.create("keystore.json", "coinbase.v3_api")

    # pyexch --params params.json --auth coinbase.v3_api --url /api/v3/brokerage/orders/historical/fills  > fills.json
    # pyexch --params params.json --auth coinbase.v3_api --url /api/v3/brokerage/products/BTC-USD/candles > candles.json

    now = int(time())
    earlier = now - (100 * 24 * 60 * 60)

    fills = cbv3.v3_client.get_fills(product_id="BTC-USD")
    candles = cbv3.v3_client.get_candles(
        product_id="BTC-USD",
        granularity="ONE_DAY",
        start=str(earlier),
        end=str(now),
    )

    date_candle = dict()
    for candle in candles["candles"]:
        epoch = int(candle["start"])
        dt = datetime.utcfromtimestamp(epoch).replace(tzinfo=timezone.utc)
        key = dt.strftime("%Y-%m-%d")
        assert not date_candle.get(key, False), "Key should be empty"
        date_candle[key] = candle

    date_fill = dict()
    for order in fills["fills"]:
        if order["side"] != "BUY" or order["trade_type"] != "FILL":
            break
        dt = datetime.strptime(order["trade_time"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(
            tzinfo=timezone.utc
        )
        key = dt.strftime("%Y-%m-%d")
        # date_fill[DATE][FILLS] = list()
        # date_fill[DATE][CANDEL] = candle
        value = date_fill.get(key, dict())
        _fills = value.get("fills", list())
        _fills += [order]
        value["fills"] = _fills
        date_fill[key] = value
        candle = date_candle.get(key)
        assert candle, "Every date should match"
        date_fill[key]["candle"] = candle

    avg_usd = ord_usd = ord_btc = 0
    for key, value in date_fill.items():
        usd = btc = 0
        for order in value["fills"]:
            fee = TAKER
            if order["liquidity_indicator"] == "MAKER":
                fee = MAKER
            btc += float(order["size"])
            usd += float(order["price"]) * float(order["size"]) * (1 + fee)
        ord_price = usd / btc
        avg_price = (
            (float(value["candle"]["open"]) + float(value["candle"]["close"]))
            / 2
            * (1 + TAKER)
        )
        print(
            f"{key}: Bought {btc:.8f} BTC at {ord_price:.2f} with daily average of {avg_price:.2f}"
        )

        ord_usd += usd
        ord_btc += btc
        avg_usd += avg_price * btc

    print(
        f"Total: Bought {ord_btc:.8f} BTC for {ord_usd/ord_btc:.2f} instead of {avg_usd/ord_btc:.2f}"
    )


if __name__ == "__main__":
    main()
