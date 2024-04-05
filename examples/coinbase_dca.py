# /bin/env python3
#
# pip install pyexch
#
from datetime import datetime, timezone

# from json import dumps
from time import sleep

from pyexch.exchange import Exchange  # , data_toDict

HOUR = 60 * 60  # one-hr in seconds

DEPOSIT = True
CANCEL_OPEN = True
SPREAD = 2 / 100  # do buys 2% below spot
TAKER = 20 / 100 * SPREAD  # let 20% of orders go as takers
THRESHOLD = 0.95  # Percent of holds to clear before starting
MKRFEE = 0.0060  # fee for maker limit orders
TKRFEE = 0.0080  # fee for taker limit orders
DCAUSD = 10.00  # USD to deposit on our DCAs
DEPSOIT_DELAY = 12 * HOUR  # If we've deposited in the last 12hrs, skip
REDUCE_TAKER = False

MAXCNT = 500  # 500 The maximum number of orders allowed
MAXCAN = 100  # 100 The maximum number of orders to cancel
MIXFEE = TAKER / SPREAD * TKRFEE + (1 - TAKER / SPREAD) * MKRFEE
PMTTYP = "ACH"
PRODID = "BTC-USD"
WALTID = "USD Wallet"
ISOFMT = "%Y-%m-%dT%H:%M:%S%z"  # Time parse formatter


def main():
    current = datetime.now().astimezone(timezone.utc)
    dcausd = DCAUSD + current.day / 100  # set pennies to day of month

    cbv3 = Exchange.create("keystore.json", "coinbase.v3_api")
    cbv3.keystore.close()  # Trezor devices should only have one handle at a time
    cboa = Exchange.create("keystore.json", "coinbase.oauth2")
    cboa.oa2_refresh()

    account_id = cboa.keystore.get("coinbase.state.usd_wallet")
    pmt_method_id = cboa.keystore.get("coinbase.state.ach_payment")

    # Get my account_id of WALTID (USD Wallet)
    #
    if not account_id:
        resp = cbv3.v3_client.get_accounts()
        for account in resp["accounts"]:
            if account["available_balance"]["currency"] == "USD" and account["name"] == WALTID:
                account_id = account["uuid"]

        assert account_id
        cboa.keystore.set("coinbase.state.usd_wallet", account_id)
        cboa.keystore.save()
        # print(f"DBG: account['name:{WALTID}']:", account_id)

    # Determine 90% funding for waitclock
    #
    balance = get_balance(cbv3, account_id)
    hold = float(cbv3._response["account"]["hold"]["value"])
    target = THRESHOLD * (hold + dcausd) + balance

    if DEPOSIT:
        # Check to see if we've deposited today
        #
        need_deposit = True
        # https://github.com/brianddk/pyexch/issues/12
        resp = cboa.oa2_client.get_deposits(account_id)
        for deposit in resp["data"]:
            # if completed or created, process
            if "canceled" == deposit["status"] or not deposit["committed"]:
                continue  # else skip

            created = datetime.strptime(deposit["created_at"], ISOFMT).astimezone(timezone.utc)
            # print(f"DBG: deposit['age_sec:{(current - created).total_seconds()}']:", deposit['id'])
            if (current - created).total_seconds() < DEPSOIT_DELAY:
                print(f"Recent Deposit of {float(deposit['amount']['amount']):.2f} found @ {deposit['created_at']}")
                need_deposit = False
                break

        # if needed, make the deposit
        #
        if need_deposit:

            # Find the PMTTYP (ACH) payment type
            #
            if not pmt_method_id:
                resp = cbv3.v3_client.list_payment_methods()
                for pmt_method in resp["payment_methods"]:
                    if pmt_method["type"] == PMTTYP:
                        pmt_method_id = pmt_method["id"]
                        break

                assert account_id and pmt_method_id
                cboa.keystore.set("coinbase.state.ach_payment", pmt_method_id)
                cboa.keystore.save()
                # print(f"DBG: payment_method['type:{PMTTYP}']:", pmt_method_id)

            # Make the deposit
            #
            resp = cboa.oa2_client.deposit(
                account_id,
                amount=f"{dcausd:.2f}",
                currency="USD",
                payment_method=pmt_method_id,
            )
            print(f"Created deposit of {float(resp['amount']['amount']):.2f} @ {resp['created_at']}")
            # print(f"DBG: deposit['amt:{dcausd}']:", dumps(data_toDict(resp)))

    if CANCEL_OPEN:
        # Get outstanding orders to cancel
        #
        resp = cbv3.v3_client.list_orders(order_status=["OPEN"])
        params = []
        for order in resp["orders"]:
            if order["status"] == "OPEN" and order["product_id"] == PRODID and order["side"] == "BUY":
                params += [order["order_id"]]

        # Cancel the outstanding orders
        #
        if params:
            sublist = [params[i : i + MAXCAN] for i in range(0, len(params), MAXCAN)]
            for params in sublist:
                resp = cbv3.v3_client.cancel_orders(order_ids=params)

    # Get today's min_size and price for PRODID (BTC-USD)
    #  https://github.com/brianddk/pyexch/issues/9
    #
    product = cbv3.v3_client.get_product(product_id=PRODID)
    if product["product_id"] == PRODID:
        min_size = float(product["base_min_size"])
        spot = float(product["price"])

    assert account_id and min_size and spot

    # Get my available balance of WALTID (USD Wallet)
    #  https://github.com/brianddk/pyexch/issues/10
    #
    adjust = 0.0 if DEPOSIT and need_deposit else THRESHOLD * dcausd
    target -= adjust
    while abs(balance - target) > 1 and balance < target:
        sleep(1)
        print(f"Waiting: balance={balance:.2f}, target={target:.2f}")
        balance = get_balance(cbv3, account_id)

    # "Peanut Butter Spread" the buys as small as possible from spot down to SPREAD (5%) below.
    #

    # price_hi = 66_857.20
    price_hi = spot * (1 + TAKER)
    price_lo = spot * (1 - SPREAD)
    price_av = (price_hi + price_lo) / 2

    count = min(int(balance / (min_size * price_av * (1 + MKRFEE))), MAXCNT)
    step = (price_hi - price_lo) / (count - 1)  # remember bookend math
    price = price_hi
    # print(spot, count, balance)
    for i in range(count, 0, -1):
        xprice = price
        uuid = cbv3.new_uuid()
        (size, cost) = mk_size(price, i, step, balance, spot, min_size)
        params = dict(
            client_order_id=str(uuid),
            product_id=PRODID,
            base_size=f"{size:.8f}",
            limit_price=f"{price:.2f}",
            post_only=True,
        )
        resp = mk_order(cbv3, params, min_size)
        if resp["order"]["status"] == "FILLED":
            cost = float(resp["order"]["total_value_after_fees"])
            xprice = float(resp["order"]["average_filled_price"])
        # balance -= cost
        cbal = balance - cost
        balance = get_balance(cbv3, account_id)
        print(f"{count} Limit buy of {params['base_size']} btc at {xprice:.2f}, at a cost of {cost:.2f}, leaving balance of {balance:.2f} ({cbal:.2f})")
        price -= step
        assert price and step and cost and balance

    return cboa


def get_balance(cbv3, account_id):
    resp = cbv3._response = cbv3.v3_client.get_account(account_id)
    if resp["account"]["available_balance"]["currency"] == "USD" and resp["account"]["name"] == WALTID:
        balance = float(resp["account"]["available_balance"]["value"])

    assert account_id and balance
    return balance


def mk_order(cbv3, params, min_size):
    retry = 3
    for i in range(retry):
        resp = cbv3.v3_client.limit_order_gtc_buy(**params)
        if resp["success"]:
            break
        if resp["error_response"]["error"] == "INVALID_LIMIT_PRICE_POST_ONLY":
            params.update(dict(post_only=False))
            if REDUCE_TAKER:
                params.update(dict(base_size=f"{min_size:.8f}"))
            for j in range(retry):
                resp = cbv3.v3_client.limit_order_gtc_buy(**params)
                if resp["success"]:
                    break

    # https://github.com/brianddk/pyexch/issues/10
    if resp["success"]:
        for i in range(retry):
            try:
                resp = cbv3.v3_client.get_order(resp["order_id"])
            except Exception:
                print("retrying")
                sleep(1)
                continue
            if resp["order"]:
                break

    return resp


def mk_size(price, count, step, balance, spot, min_size):
    price_hi = price
    price_lo = price - step * (count - 1)
    price_av = (price_hi + price_lo) / 2
    size = (balance - count / 100) / count / (price_av * (1 + MKRFEE))
    if price > spot:
        if REDUCE_TAKER:
            size = min_size
        cost = size * spot * (1 + TKRFEE)
    else:
        cost = size * price * (1 + MKRFEE)
    return (size, cost)


if __name__ == "__main__":
    # main()
    try:
        cboa = main()
    except Exception as e:
        import traceback

        print(
            traceback.format_exc(),
            "\n#### Debugger (q) to quit ####",
            "\n#### Exception in object (ex) ####",
        )
        ex = e
        breakpoint()  # main debug hook
