# /bin/env python3
#
# pip install pyexch
#

# from json import dump, dumps
# from pyjson5 import load, loads

from datetime import datetime, timezone
from time import time

from pyexch.exchange import Exchange  # , data_toDict

MAKER = 0.006
TAKER = 0.008
COUNT = 10_000


def main():
    cbv3 = Exchange.create("keystore.json", "coinbase.v3_api")

    # pyexch --params params.json --auth coinbase.v3_api --url /api/v3/brokerage/orders/historical/fills  > fills.json
    # pyexch --params params.json --auth coinbase.v3_api --url /api/v3/brokerage/products/BTC-USD/candles > candles.json

    now = int(time())
    earlier = now - (100 * 24 * 60 * 60)

    cursor = ""
    fills = dict(fills=list())
    while len(fills["fills"]) < COUNT:
        resp = cbv3.v3_client.get_fills(product_id="BTC-USD", cursor=cursor)
        cursor = resp["cursor"]
        fills["fills"] += resp["fills"]
        if not cursor:
            break

    candles = cbv3.v3_client.get_candles(
        product_id="BTC-USD",
        granularity="ONE_DAY",
        start=str(earlier),
        end=str(now),
    )
    spot = float(candles["candles"][0]["close"]) * (1 + TAKER)

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
        # https://github.com/brianddk/pyexch/issues/5
        try:
            dt = datetime.strptime(
                order["trade_time"], "%Y-%m-%dT%H:%M:%S.%fZ"
            ).replace(tzinfo=timezone.utc)
        except ValueError:
            dt = datetime.strptime(order["trade_time"], "%Y-%m-%dT%H:%M:%SZ").replace(
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

    buc_btc = avg_usd = ord_usd = ord_btc = 0
    for key, value in date_fill.items():
        usd = btc = 0
        for order in value["fills"]:
            # fee = TAKER
            # if order["liquidity_indicator"] == "MAKER":
            # fee = MAKER
            btc += float(order["size"])
            usd += float(order["price"]) * float(order["size"]) + float(
                order["commission"]
            )
        ord_price = usd / btc
        avg_price = (
            (float(value["candle"]["open"]) + float(value["candle"]["close"]))
            / 2
            * (1 + TAKER)
        )
        print(
            f"{key}: Bought {btc:.8f} BTC at {ord_price:.2f} instead of {avg_price:.2f}"
        )

        ord_usd += usd
        ord_btc += btc
        avg_usd += avg_price * btc
        buc_btc += 1 / avg_price

    count = len(date_fill.keys())
    saved_usd = avg_usd - ord_usd
    saved_pct = saved_usd / avg_usd * 100
    saved_dca = (ord_btc - (buc_btc * ord_usd / count)) / ord_btc * 100

    print(
        f"Total: Bought {ord_btc:.8f} BTC for {ord_usd/ord_btc:.2f} instead of {avg_usd/ord_btc:.2f}"
    )
    print(
        f"   Saving {saved_pct:.4f}% (${saved_usd:.2f}) vs buy-on-avg, and {saved_dca:.4f}% vs dca-market-buy"
    )
    print(
        f"   Saving {100-(ord_usd/ord_btc)/spot*100:.2f}% vs one-time market buy at current price of: {spot:.2f}"
    )


if __name__ == "__main__":
    # main()
    try:
        main()
    except Exception as e:
        import traceback

        print(
            traceback.format_exc(),
            "\n#### Debugger (q) to quit ####",
            "\n#### Exception in object (ex) ####",
        )
        ex = e
        breakpoint()
