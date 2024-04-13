# Send Bitcoin from console

After some of the website downtime in April and inability to send funds through the web-app and mobile-app, I went ahead and added code for `CB-2FA-Token` headers to allow me to use the [Send Money][a] API endpoint (`/v2/accounts/${account_id}/transactions`).  A costly endeavor since transaction fees are high, but worth it in the end since I now have a way to withdraw funds if CB-Web or CB-Mobile lock up again.

Here's a walkthough if anyone wants to use it.  This assumes API-keys with proper scope are already created and added to an encrypted keystore file.  Same process can be done in curl with very little modification, but I wrote this so I could stop using curl for this stuff.  One thing I hate is that the **Send Money** endpoint requires 2FA and does NOT support Yubikey.  So I have to downgrade my 2FA to Authenticator, which does kind-of make it worthless.  But perhaps if CB-Web crashes I can still hit [coinbase/security][b] and adjust my 2FA.

To setup the API keys and create an encrypted keystore, thumb through the [README][c] file on the [pyexch][d] repo

[a]: https://docs.cloud.coinbase.com/sign-in-with-coinbase/docs/api-transactions#send-money
[b]: https://accounts.coinbase.com/security
[c]: https://github.com/brianddk/pyexch?tab=readme-ov-file#pyexch
[d]: https://github.com/brianddk/pyexch

Here are the three commands to perform a BTC transaction from console:

### Get the Bitcoin account UUID

    $ pyexch \
        --url /api/v3/brokerage/accounts \
        | jq '.accounts[] | select(.currency=="BTC")'
    "456789ab-cdef-0123-4567-89abcdef0123"

### Make a fresh idem UUID

    $ pyexch --call new_uuid
    bcdef012-3456-789a-bcde-f0123456789a

### Create params.json5

    {
      "type": "send",
      "currency": "BTC",
      "description": "Test send to brianddk tipjar",

      // brianddk tipjar
      "to": "bc1qwc2203uym96u0nmq04pcgqfs9ldqz9l3mz8fpj",

      // About ~ $10
      "amount": "0.00015000",

      // pyexch --call new_uuid
      "idem": "bcdef012-3456-789a-bcde-f0123456789a",
    }

### Send Funds

    $ pyexch \
        --params params.json5 \
        --method post \
        --url /v2/accounts/456789ab-cdef-0123-4567-89abcdef0123/transactions
    {
      "errors": [
        {
          "id": "two_factor_required",
          "message": "Two-step verification code required to complete this request. Re-play the request with CB-2FA-Token header."
        }
      ]
    }
    Enter 2FA token: 456789
    {
      "data": {
        "id": "9abcdef0-1234-5678-9abc-def012345678",
        "type": "send",
        "status": "pending",
        "amount": {
          "amount": "-0.00036812",
          "currency": "BTC"
        },
        "native_amount": {
          "amount": "-24.67",
          "currency": "USD"
        },
        "description": "Test send to brianddk tipjar",
        "created_at": "2024-04-13T00:15:58Z",
        "updated_at": "2024-04-13T00:15:58Z",
        "resource": "transaction",
        "resource_path": "/v2/accounts/456789ab-cdef-0123-4567-89abcdef0123/transactions/9abcdef0-1234-5678-9abc-def012345678",
        "instant_exchange": false,
        "network": {
          "status": "pending",
          "status_description": "Pending (est. about 30 minutes)",
          "transaction_fee": {
            "amount": "0.00021812",
            "currency": "BTC"
          },
          "transaction_amount": {
            "amount": "0.00015000",
            "currency": "BTC"
          },
          "confirmations": 0
        },
        "to": {
          "resource": "phone",
          "address": "bc1qwc2203uym96u0nmq04pcgqfs9ldqz9l3mz8fpj",
          "currency": "BTC",
          "address_info": {
            "address": "bc1qwc2203uym96u0nmq04pcgqfs9ldqz9l3mz8fpj"
          },
          "address_url": "https://blockchain.info/address/bc1qwc2203uym96u0nmq04pcgqfs9ldqz9l3mz8fpj"
        },
        "idem": "bcdef012-3456-789a-bcde-f0123456789a",
        "application": {
          "id": "3456789a-bcde-f012-3456-789abcdef012",
          "resource": "application",
          "resource_path": "/v2/applications/3456789a-bcde-f012-3456-789abcdef012"
        },
        "details": {
          "title": "Sent Bitcoin",
          "subtitle": "To Bitcoin address on Bitcoin network",
          "header": "Sent 0.00036812 BTC ($24.67)",
          "health": "warning"
        },
        "hide_native_amount": false
      }
    }
