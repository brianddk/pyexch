from datetime import datetime, timezone

from pyexch.exchange import Exchange  # , data_toDict

ISOFMT = "%Y-%m-%dT%H:%M:%S%z"  # Time parse formatter


def main():
    cboa = Exchange.create("keystore.json", "coinbase.oauth2")
    cboa.oa2_refresh()

    deltas = list()
    account_id = cboa.keystore.get("coinbase.state.usd_wallet")
    resp = cboa.oa2_client.get_deposits(account_id)
    for deposit in resp["data"]:
        if deposit.get("committed") and deposit.get("hold_until") and deposit.get("status") != "canceled":
            created = datetime.strptime(deposit["created_at"], ISOFMT).astimezone(timezone.utc)
            hold = datetime.strptime(deposit["hold_until"], ISOFMT).astimezone(timezone.utc)
            deltas += [(hold - created).total_seconds()]

    print(f"Average days hold: {sum(deltas)/(len(deltas)*60*60*24):.2f}")


if __name__ == "__main__":
    main()
