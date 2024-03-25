# /bin/env python3
#
# pip install pyexch
#
from pyexch.exchange import Exchange
from json import loads, dumps
from time import sleep
from datetime import datetime, timezone

HOUR   = 60 * 60    # one-hr in seconds

TAKER  = 0.01       # do buys 1% above market (taker action)
SPREAD = 0.06       # do buys 1% above to 5% below (peanut butter spread)
MKRFEE = 0.0040     # fee for maker limit orders
TKRFEE = 0.0060     # fee for taker limit orders
DCAUSD = 10.14      # USD to deposit on our DCAs
DEPOSIT = True
CANCEL_OPEN = True
DEPSOIT_DELAY = 12 * HOUR  # If we've deposited in the last 12hrs, skip

MIXFEE = TAKER/SPREAD * TKRFEE + (1 - TAKER/SPREAD) * MKRFEE
PMTTYP = "ACH"
PRODID = "BTC-USD"
WALTID = "USD Wallet"
ISOFMT = "%Y-%m-%dT%H:%M:%S%z"  # Time parse formatter

current = datetime.now().astimezone(timezone.utc)

cbv3 = Exchange.create('keystore.json', 'coinbase.v3_api')
cbv3.keystore.close()  # Trezor devices should only have one handle at a time
cboa = Exchange.create('keystore.json', 'coinbase.oauth2')

if CANCEL_OPEN:
    # Get outstanding orders to cancel
    #
    resp = cbv3.v3_client.list_orders(order_status=["OPEN"])
    params = []
    for order in resp['orders']:
        if order['status'] == "OPEN" and order['product_id'] == PRODID and order['side'] == "BUY":
            params += [order['order_id']]

    # Cancel the outstanding orders
    #
    if params:
        resp = cbv3.v3_client.cancel_orders(order_ids=params)      

# Get my account_id of WALTID (USD Wallet)
#
resp = cbv3.v3_client.get_accounts()
for account in resp['accounts']:
    if (account['available_balance']['currency'] == "USD" and account['name'] == WALTID):
        account_id = account['uuid']

assert account_id
        

if DEPOSIT:
    # Check to see if we've deposited today
    #
    need_deposit = True
    resp = cboa.oa2_client.get_deposits(account_id)
    for deposit in resp['data']:
        created = datetime.strptime(deposit['created_at'], ISOFMT).astimezone(timezone.utc)
        if (current - created).total_seconds() < :
            need_deposit = False
            break

    # if needed, make the deposit
    #
    if need_deposit:

        # Find the PMTTYP (ACH) payment type
        #
        resp = cbv3.v3_client.list_payment_methods()
        for pmt_method in resp['payment_methods']:
            if pmt_method['type'] == PMTTYP:
                pmt_method_id = pmt_method['id']
                break
            
        assert account_id and pmt_method_id

        # Make the deposit
        #
        resp = cboa.oa2_client.deposit(account_id, amount=f"{DCAUSD:.2f}", currency="USD", payment_method=pmt_method_id)

sleep(3) # There really is a settle time from cancel to avail balance... insane.

# Get my available balance of WALTID (USD Wallet)
#
resp = cbv3.v3_client.get_account(account_id)
if (resp['account']['available_balance']['currency'] == "USD" and resp['account']['name'] == WALTID):
    avail = float(resp['account']['available_balance']['value']) 
    balance = avail * (1-MKRFEE)

assert account_id and avail

# Get today's min_size and price for PRODID (BTC-USD)
#
resp = cbv3.v3_client.get_products()
for product in resp['products']:
    if product['product_id'] == PRODID:
        min_size = float(product['base_min_size'])
        price = float(product['price'])
        break

assert account_id and avail and min_size and price
price *= (1 + TAKER) # Allow some taker action

# "Peanut Butter Spread" the buys as small as possible from spot down to SPREAD (5%) below.
# 
median = price * (1 - SPREAD/2)
count = int(balance / (min_size * median))
min_size = (balance / median) / count
step = median * (SPREAD / count)
buy = 0
print("[") # ensure the stdout is JSON5 parsable
for i in range(count):
    sep = "," if i else ""
    uuid = cbv3.new_uuid()
    price -= step
    buy += price * min_size
    params=dict(
        client_order_id = str(uuid),
        product_id = PRODID,
        base_size = f"{min_size:.8f}",
        limit_price = f"{price:.2f}",
        post_only = False
    )
    resp = cbv3.v3_client.limit_order_gtc_buy(**params)   
    if resp: print(sep, dumps(resp, indent=2))

print("]") # ensure the stdout is JSON5 parsable

