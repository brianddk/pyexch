from json import dumps

from pyexch.exchange import Exchange

EARLIEST = 1437428220  # ONE_MINUTE;     Mon Jul 20 2015 21:37:00 GMT
EARLIEST = 1437428100  # FIVE_MINUTE;    Mon Jul 20 2015 21:35:00 GMT
EARLIEST = 1437427800  # FIFTEEN_MINUTE; Mon Jul 20 2015 21:30:00 GMT
EARLIEST = 1563840000  # THIRTY_MINUTE;  Tue Jul 23 2019 00:00:00 GMT
EARLIEST = 1437426000  # ONE_HOUR;       Mon Jul 20 2015 21:00:00 GMT
EARLIEST = 1563840000  # TWO_HOUR;       Tue Jul 23 2019 00:00:00 GMT
EARLIEST = 1437415200  # SIX_HOUR;       Mon Jul 20 2015 18:00:00 GMT
EARLIEST = 1437350400  # ONE_DAY;        Mon Jul 20 2015 00:00:00 GMT
LIMIT = 300
COUNT = 2000


def main():
    cbv3 = Exchange.create("keystore.json", "coinbase.v3_api")
    cbv3.keystore.close()  # Trezor devices should only have one handle at a time

    # pyexch --params params.json --auth coinbase.v3_api --url /api/v3/brokerage/products/BTC-USD/candles > candles.json

    tests = dict(
        ONE_MINUTE=dict(tick=1 * 60),
        FIVE_MINUTE=dict(tick=5 * 60),
        FIFTEEN_MINUTE=dict(tick=15 * 60),
        THIRTY_MINUTE=dict(tick=30 * 60),
        ONE_HOUR=dict(tick=1 * 60 * 60),
        TWO_HOUR=dict(tick=2 * 60 * 60),
        SIX_HOUR=dict(tick=6 * 60 * 60),
        ONE_DAY=dict(tick=24 * 60 * 60),
    )

    for tag, obj in tests.items():
        tick = obj["tick"]
        earliest = EARLIEST
        end = earliest
        end -= end % tick
        start = end - (LIMIT - 1) * tick

        for i in range(COUNT):
            params = dict(
                product_id="BTC-USD",
                granularity=tag,
                start=str(start),
                end=str(end),
            )
            resp = cbv3.v3_client.get_candles(**params)
            if len(resp["candles"]):
                break

            start = end
            end += (LIMIT - 1) * tick

        print(f"tag: {tag}, i: {i}, len: {len(resp['candles'])}, ", end="")

        if i + 1 == COUNT:
            print("")
        else:
            earliest = resp["candles"][-1]["start"]
            tests[tag]["earliest"] = earliest
            print(f"earliest: {earliest}")

        print(dumps(tests, indent=2))


if __name__ == "__main__":
    main()
