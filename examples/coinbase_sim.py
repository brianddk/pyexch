# /bin/env python3
#
# pip install pyexch
#

# from json import dump, dumps
# from pyjson5 import load, loads

# from datetime import datetime, timezone
from time import time

from pyexch.exchange import Exchange  # , data_toDict

MAKER = 0.006
TAKER = 0.008
COUNT = 400  # bugcheck ~3200, keep below that.
DAY_TICK = 24 * 60 * 60
LIMIT = 100


def main():
    cbv3 = Exchange.create("keystore.json", "coinbase.v3_api")

    # pyexch --params params.json --auth coinbase.v3_api --url /api/v3/brokerage/products/BTC-USD/candles > candles.json

    now = int(time())
    earlier = now - (min(LIMIT, COUNT) * DAY_TICK)

    params = dict(
        product_id="BTC-USD",
        granularity="ONE_DAY",
        start=str(earlier),
        end=str(now),
    )
    candles = dict(candles=list())
    while len(candles["candles"]) < COUNT:
        resp = cbv3.v3_client.get_candles(**params)
        candles["candles"] += resp["candles"]
        end = int(resp["candles"][-1]["start"]) - DAY_TICK
        start = end - LIMIT * DAY_TICK
        params.update(
            dict(
                start=str(start),
                end=str(end),
            )
        )

    i = 0
    dip = list()
    for day in candles["candles"]:
        open = float(day["open"])
        low = float(day["low"])
        dip += [(open - low) / open]
        # print(f"i:{i}, open: {open:.2f}, low: {low:.2f}, dip: {dip[-1] * 100:.2f}")
        i += 1

    dip.sort()
    percent = 10 / 100  # 10%
    i = int(len(dip) * percent / 2)
    tdip = dip[i:-i]
    print(f"Regular average dip: {sum(dip)/len(dip) * 100:.4f}%")
    print(
        f"Trimmed ({percent*100:.0f}%, {2*i} of {len(dip)}) average dip: {sum(tdip)/len(tdip) * 100:.4f}%"
    )
    print(f"Approximate median dip of: {dip[int(len(dip)/2)+1] * 100:.4f}%")

    # breakpoint()


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
