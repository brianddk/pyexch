from pyexch.exchange import Exchange


def main():
    cbv2 = Exchange.create("keystore.json", "coinbase.v2_api")
    cbv2.keystore.close()  # Don't keep two dirty keystores open to the same backend
    cboa = Exchange.create("keystore.json", "coinbase.oauth2")

    done = False
    for client in [cbv2, cboa]:
        if done:
            break
        accts = client.get("/v2/accounts")
        for account in accts["data"]:
            if done:
                break
            acct_id = account["id"]
            addrs = client.get(f"/v2/accounts/{acct_id}/addresses")
            for address in addrs["data"]:
                if done:
                    break
                addr_id = address["id"]
                txns = client.get(f"/v2/accounts/{acct_id}/addresses/{addr_id}/transactions")
                count = len(txns["data"])
                if count:
                    for txn in txns["data"]:
                        if done:
                            break
                        txn_id = txn["id"]
                        done = True

    assert txn_id and addr_id and acct_id
    cboa.keystore.set("coinbase.test.acct_id", acct_id)
    cboa.keystore.set("coinbase.test.addr_id", addr_id)
    cboa.keystore.set("coinbase.test.txn_id", txn_id)
    cboa.keystore.save()


if __name__ == "__main__":
    main()
