from json import dumps

from pyexch.exchange import Exchange


def get_tag(default):
    if default == "coinbase.v2_api":
        return "CBV2"
    if default == "coinbase.oauth2":
        return "CBOA"


def get_args(obj):
    if type(obj) is dict:
        return (obj["url"], obj["params"])
    else:
        return (obj, None)


cbv2 = Exchange.create("keystore.json", "coinbase.v2_api")
cbv2.keystore.close()
cbv3 = Exchange.create("keystore.json", "coinbase.v3_api")
cbv3.keystore.close()
cboa = Exchange.create("keystore.json", "coinbase.oauth2")
cboa.oa2_refresh()

asset_id = "BTC"
user_id = cboa.keystore.get("coinbase.test.user_id")
account_id = cboa.keystore.get("coinbase.test.acct_id")
addr_id = cboa.keystore.get("coinbase.test.addr_id")
txn_id = cboa.keystore.get("coinbase.test.txn_id")
zrx_acc_id = cboa.keystore.get("coinbase.test.zrx_acct")


def main():
    cbv2_urls = dict(
        get=dict(
            success=[
                "https://api.coinbase.com/v2/user",  # Show Current User
                "https://api.coinbase.com/v2/user/auth",  # Show Auth
                "https://api.coinbase.com/v2/accounts",  # List Accounts
                f"https://api.coinbase.com/v2/accounts/{account_id}",  # Show Account
                f"https://api.coinbase.com/v2/accounts/{account_id}/addresses",  # List Addresses
                f"https://api.coinbase.com/v2/accounts/{account_id}/addresses/{addr_id}",  # Show Address
                f"https://api.coinbase.com/v2/accounts/{account_id}/addresses/{addr_id}/transactions",  # List Transactions
                f"https://api.coinbase.com/v2/accounts/{account_id}/transactions/{txn_id}",  # Show Transaction
            ],
            failure=[
                f"https://api.coinbase.com/v2/user/{user_id}",  # Show User
                # f"https://api.coinbase.com/v2/accounts/{asset_id}",                                           # SKIP Create Wallet, this works even though it shouldn't (bugbug scope)
            ],
        ),
        # SKIP Create Address, works, tried one-shot manually
        # SKIP Send Money
        # SKIP Transfer Money
        put=dict(
            success=[],
            failure=[
                dict(
                    url=f"https://api.coinbase.com/v2/accounts/{zrx_acc_id}",  # Update Account
                    params=dict(name="ZRX Wallet--"),
                ),
            ],
        ),
        delete=dict(
            success=[],
            failure=[
                dict(
                    url=f"https://api.coinbase.com/v2/accounts/{zrx_acc_id}",  # Delete Account
                    params=None,
                ),
            ],
        ),
    )

    for client in [cbv2, cboa]:
        for method in [client.get, client.put, client.delete]:
            label = method.__func__.__name__
            LABEL = label.upper()
            TAG = get_tag(client.keystore.get("default"))
            print(f"################## {LABEL}S ###################")
            for obj in cbv2_urls[label]["success"]:
                uri, params = get_args(obj)
                resp = method(uri)
                assert resp, f"Failed on expected {LABEL}.success: {uri}"
                print(f"{TAG} {len(dumps(resp)):06}", uri)

            for obj in cbv2_urls[label]["failure"]:
                uri, params = get_args(obj)
                try:
                    resp = method(uri)
                    assert False, "Succeeded where we should have failed"
                except Exception as e:
                    print(f"{TAG} catch:", uri, e)
                    # ex = e
                    # breakpoint()  ; Individual call breakpoint


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
