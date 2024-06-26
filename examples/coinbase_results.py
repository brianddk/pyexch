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
MXDAY = 300 - 1  # bookend math
ISOFMT = "%Y-%m-%dT%H:%M:%S%z"  # Time parse formatter
ONE_DAY = 24 * 60 * 60


def main():
    cbv3 = Exchange.create("keystore.json", "coinbase.v3_api")
    cbv3.keystore.close()  # Trezor devices should only have one handle at a time
    cboa = Exchange.create("keystore.json", "coinbase.oauth2")
    cboa.oa2_refresh()

    # pyexch --params params.json --auth coinbase.v3_api --url /api/v3/brokerage/orders/historical/fills  > fills.json
    # pyexch --params params.json --auth coinbase.v3_api --url /api/v3/brokerage/products/BTC-USD/candles > candles.json

    now = int(time())
    now -= now % ONE_DAY
    earlier = now - (MXDAY * ONE_DAY)

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
            dt = datetime.strptime(order["trade_time"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)
        except ValueError:
            dt = datetime.strptime(order["trade_time"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
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
            usd += float(order["price"]) * float(order["size"]) + float(order["commission"])
        ord_price = usd / btc
        avg_price = (float(value["candle"]["open"]) + float(value["candle"]["close"])) / 2 * (1 + TAKER)
        print(f"{key}: Bought {btc:.8f} BTC at {ord_price:.2f} instead of {avg_price:.2f}")

        ord_usd += usd
        ord_btc += btc
        avg_usd += avg_price * btc
        buc_btc += 1 / avg_price

    saved_usd = avg_usd - ord_usd
    saved_pct = saved_usd / avg_usd * 100

    dca_usd = dca_btc = 0.0
    account_id = cboa.keystore.get("coinbase.state.usd_wallet")
    resp = cboa.oa2_client.get_deposits(account_id)
    for deposit in resp["data"]:
        # if completed or created, process
        if "canceled" == deposit["status"] or not deposit["committed"]:
            continue  # else skip

        created = datetime.strptime(deposit["created_at"], ISOFMT).astimezone(timezone.utc)

        if 2024 != created.year:
            continue

        dep_time = str_to_time(deposit["created_at"])
        dep_time -= dep_time % 60
        params = dict(
            product_id="BTC-USD",
            granularity="ONE_MINUTE",
            start=str(dep_time),
            end=str(dep_time + 59),
        )
        candles = cbv3.v3_client.get_candles(**params)
        candle = candles["candles"][0]
        avg = (
            (1 + TAKER)
            / 4
            * sum(
                [
                    float(candle["open"]),
                    float(candle["close"]),
                    float(candle["low"]),
                    float(candle["high"]),
                ]
            )
        )
        amt = float(deposit["amount"]["amount"])
        dca_usd += amt
        dca_btc += amt / avg

    ord_price = ord_usd / ord_btc
    dca_price = dca_usd / dca_btc
    saved_dca = (dca_price - ord_price) / dca_price

    print(f"Total: Bought {ord_btc:.8f} BTC for {ord_usd/ord_btc:.2f} instead of {avg_usd/ord_btc:.2f}")
    print(f"   Saving {saved_pct:.2f}% vs buy-on-avg, and {saved_dca:.6f}% vs dca-market-buy")
    print(f"   Saving {100-(ord_usd/ord_btc)/spot*100:.2f}% vs one-time market buy at current price of: {spot:.2f}")
    print(f"DCA deposits: {dca_usd:.2f}\nDCA bought: {ord_usd:.2f}")


def str_to_time(time_str):
    dt_obj = datetime.strptime(time_str, ISOFMT).astimezone(timezone.utc)
    return int(dt_obj.timestamp())


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
        breakpoint()  # main debug hook
