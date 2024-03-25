What follows is a walkthrough of doing a "normal" daily interaction with coinbase, but this time it is done completely through the APIs.  To do this I'm using a utility called [pyexch][x] but honestly it is only a very loose wrapper around `curl`.  You could do this all through `curl` with just a few modifications, but I wrote [pyexch][x] to do many of the shortcuts for me.

Main motivation for doing "Coinbase by Hand" is to take advantage of the verbose data in the API and to be less reliant on the flaky Website and Mobile app.  This is a learning example, I also have my actually working DCA script posted under [examples][y] if you want to review it as well.

## Check your keystore.json for pyexch

See the pyexch [README][z] for instructions on creating a `keystore.json` file.  But before we do anything we need to add an ACH bank at: `coinbase.com/settings/linked-accounts`.  This cannot be done with [pyexch][x] but rather must be done either on CB-Web or CB-App.  Once we've verified with have an ACH payment method we will work to ensure we have all the credentials we need.  We will do everything with OAuth2, since it works on both V2 and V3 URLs.  In the following `print_keystore` call, we are masking off private data using a `redactions.json5` template available in the pyexch [templates][a] directory

### Print our Keystore

    pyexch --params redactions.json5 --call print_keystore
    
Next we need to ensure our OAuth2 session has the proper scopes enabled.   Namely `{wallet:payment-methods:read, wallet:accounts:read, wallet:deposits:read, wallet:deposits:create, wallet:buys:create}`.  So we will dump our current OAuth2 scopes and see if we have what we need.

### Verify our Scopes

    pyexch --auth coinbase.oauth2 \
      --url https://api.coinbase.com/v2/user/auth
  
If we need to add scope, we can't do that directly with encrypted keystores.  We need to make the changes in an update template then apply those to our keystore.

### Update our Keystore

    pyexch --params updates.json5 --call update_keystore
    
If we did change scopes, we need new OAuth2 tokens with the new scope.  This will launch a local webserver to handle the callback.

### Get a new OAuth2 with new Scopes

    pyexch --url https://api.coinbase.com/oauth/authorize
    

## Make your deposit

Next we will check our payment methods to find our ACH account (USA).  We need the `id` of the payment method of `type` ACH.

### Find our ACH Payment Method

    pyexch --url /api/v3/brokerage/payment_methods

We will reference that saved id as `pmt_method_id` and pretend the value is something like `def0...`

Next, we need to find find our "USD Wallet" account.  We'll dump all the accounts and look for the `name` of "USD Wallet" then save off the `uuid` for that account.

### Find our USD Wallet

    pyexch --url /api/v3/brokerage/accounts
    
We will reference that saved uuid as `usd_acct` and pretend the value is something like `bcde...`

Now we will create a parameter JSON5 file to feed to our deposit command.  We will put our USD amount and `pmt_method_id` in this file.  Make your `deposit_funds.json5` params file as follows:

### Make our Deposit Params

    {
      // pmt_method_id = "def0..."
      "payment_method": "def01234-5678-9abc-def0-123456789abc",
      "amount": "100.24",
      "currency": "USD",
      "commit": false
    }


Since we specified `commit=false` this deposit command will only make a preview.  We will need to commit the preview later to complete the deposit.  Notice we use our `deposit_funds.json5` file which has our `pmt_method_id` but we also put our `usd_acct` that we also gathered earlier.

### Preview our Deposit

    # /v2/accounts/bcde.../deposits
    pyexch \
      --params deposit_funds.json5 \
      --method post \
      --url /v2/accounts/${usd_acct}/deposits 
  
The response JSON created a new ID in the top level JSON that we will now refer to as `deposit_id`.  We'll pretend the value for that id lools like `0123...`.  So also need to review the rest of the deposit information and if you are satisfied with your deposit commit it, we can commit it as follows.  Notice that the commit URL is similar but now includes the `depsoit_id`.

### Commit our Deposit

    # /v2/accounts/bcde.../deposits/0123.../commit
    pyexch \
      --params deposit_funds.json5 \
      --method post \
      --url /v2/accounts/${usd_acct}/deposits/${deposit_id}/commit
  
Take note in the return JSON.  This has much richer information than most other interfaces.  Pay close attention to the `data.hold_until` field.  This is when the funds may be available.  In my experience, you can still trade on un-available funds, they just tend to taint your proceeds with holds is all.
  
# Set your limit order

Now we have set up our keystore, and made an ACH deposit, we are ready to make a limit order.  Obviously the other steps likely don't need to be redone for a while, and you can save off `pmt_method_id` and `usd_acct` since those identifiers will persist until they transition from the current v3 API, to some future v4 API.  For our order, we'll operate on the "BTC-USD" order book to perform a "BUY" limit order to buy 0.000030 BTC when the price drops to $45000.  Create a fresh UUID that you will need for your deposit.  Obviously you may want to do a larger order, but this is just an example.  First we to generate a random UUID to use for the order.

### Get a fresh UUID

    pyexch --call new_uuid

You should now see a fresh random UUID.  We'll pretend the value looks like `cdef...`.  Now we create a new parameter file called `create_order.json5` that will hold our new UUID as well as our order instructions:

### Make our Order Params

    {
      "client_order_id": "cdef0123-4567-89ab-cdef-0123456789ab",
      "product_id": "BTC-USD",
      "side": "BUY",
      "order_configuration": {
        "limit_limit_gtc": {
          "base_size": "0.000030",
          "limit_price": "45000",
          "post_only": true
        }
      }
    }

We now have everything wee need to create the order on the BTC-USD book.

### Place our Order

    pyexch --params create_order.json5 \
      --method post --url /api/v3/brokerage/orders

You can see your order at: `coinbase.com/orders`

[z]: https://github.com/brianddk/pyexch/blob/main/README.md
[y]: https://github.com/brianddk/pyexch/tree/main/examples
[a]: https://github.com/brianddk/pyexch/tree/main/templates
[x]: https://github.com/brianddk/pyexch