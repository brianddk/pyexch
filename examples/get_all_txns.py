#!/usr/bin/env python3
from json import dump

# pip install git+https://github.com/brianddk/pyexch.git
from pyexch.exchange import Exchange

cboa = Exchange.create("keystore.json")

accounts = dict()
for url in ["/v2/accounts", "/api/v3/brokerage/accounts"]:
    resp = cboa.get(url)
    data = resp.get("data", resp.get("accounts"))
    for account in data:
        name = account["name"]
        id = account.get("id", account.get("uuid"))
        if id and accounts.get(name):
            assert id == accounts.get(name), "Account ids don't match"
        accounts[name] = id

transactions = dict()
for name, id in accounts.items():
    params = dict(limit=100)
    transactions[name] = data = list()
    starting_after = True
    while starting_after:
        try:
            resp = cboa.get(f"/v2/accounts/{id}/transactions", params=params)
            print(name, id, starting_after)
        except Exception:
            print(name, id, "NOT FOUND")
            break
        starting_after = resp["pagination"]["next_starting_after"]
        params["starting_after"] = starting_after
        data += resp["data"]

with open("all_txns.json", "w") as vj:
    dump(transactions, vj)

print("written")
