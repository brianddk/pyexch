# pyexch

[![PyPI version](https://badge.fury.io/py/pyexch.svg)](https://badge.fury.io/py/pyexch)
[![License](https://img.shields.io/badge/License-Apache%202.0-green.svg)](https://opensource.org/license/apache-2-0/)
[![GitHub](https://img.shields.io/badge/GitHub-Repo-blue.svg)](https://github.com/brianddk/pyexch)
[![GitHub Discussions](https://img.shields.io/badge/GitHub-Discussions-blue.svg)](https://github.com/brianddk/pyexch/discussions)
[![Donate with Bitcoin Lightning](https://img.shields.io/badge/Donate-Lightning-yellow.svg)](https://tippin.me/@dkbriand)
[![Donate with Bitcoin](https://img.shields.io/badge/Donate-Bitcoin-orange.svg)](https://mempool.space/address/bc1qwc2203uym96u0nmq04pcgqfs9ldqz9l3mz8fpj)

***EARLY PREVIEW RELEASE*** of a rudimentary python CLI based rest client for Coinbase

```
usage: pyexch [-h] [--method <get,post,>] [--url https://...]
              [--params params.json] [--call get_accounts]
              [--keystore ks.json] [--auth exch.auth]

Python Exchange CLI (pyexch)

optional arguments:
  -h, --help            show this help message and exit
  --method <get,post,>  rest http method (get<default>,post,put,delete)
  --url https://...     rest http url to perform actions upon
  --params params.json  json(5) filename holding rest parameters / data
  --call get_accounts   call method in the default client
  --keystore ks.json    json(5) filename where secrets are stored (backup!)
  --auth exch.auth      the auth method to use from keystore.

NOTE: Must name either "--call" or "--url", but not both, and "keystore.json"
is assumed if "--keystore" is not named
```

## Future Plans

- [x] Add PUT and DELETE methods for Coinbase (untested)
- [x] Mask input on private data so it's is muted on screen
- [ ] Add [AES encryption][n], or port samples to [CryptoDomeX][o]
- [ ] Add Kraken as a supported Exchange
- [ ] Add Binance as a supported Exchange (from USA ?!?)

## Install and Initial Setup

This utility allows you to use a Cryptocurrency Exchange's REST API to perform basic tasks and retrieve current and historical account data.  You will need to setup API / OAuth2 access keys in your account to use this utility.  The utility supports both GPG and Trezor-CipherKeyValue encryption.  You will need either a GPG key pair installed, or a Trezor attached.  As a fallback you can store API keys in naked JSON, but that is obviously not recommended.

### Install with Debug support

If you want to debug one of the client calls or step into a [requests][j] call, you can install from GIT sources.  Then you can add breakpoints in source using calls to `breakpoint()` to get more detailed information.

1. Get source: `git clone https://github.com/brianddk/pyexch.git`
2. Switch directories: `cd pyexch`
3. Install develop mode via pip: `pip install -e .`
4. Verify install (cli-mode): `pyexch --help`
5. Optionally add `breakpoint()` into one of the `*.py` files
6. Optionally step through code in the python debugger (`pdb`)

### Install without GIT

To install the most recent edition directly from GitHub tarball:

```
pip install https://github.com/brianddk/pyexch/archive/refs/heads/main.tar.gz
```

You won't get to documentation or templates, but all the code will land and function 

### Install last release from PIP

1. Install: `pip install pyexch`
2. Verify install: `pyexch --help`

Alternatively you can run it in module mode (`python -m pyexch --help`) or run the script directly (`python pyexch.py --help`).

## Building a Keystore

If you decide to use a naked JSON, you can simply modify the `null` values in the `json_ks.json` to fill in the key values.  If you want to use encryption you will need to modify on of the encryption templates (`trezor_ks.json` or `gnupg_ks.json`) and update the unencrypted parameters.  These all deal with various encryption settings.  Note that for Trezor, `zlib` is the ONLY supported compression.  Since the JSON keystore is self explanatory, I'll focus on building the encrypted keystores.

### Building a GnuPG encrypted Keystore:

Start with the GnuPG template `gnupg_ks.json`, and change the recipient to the key-id of your GnuPG key.  This can be the UID (email), or the short or long key hex.

```
{
  "format": "gnupg",
  "gnupg": {
    "recipient": "TYPE_YOUR_GPG_PUBLIC_KEY_HERE"
  }
}
```

Once you have populate the recipient, you can update the secrets interactively to keep them off of your filesystem and out of your process viewer.  This uses the `update_keystore` command which takes a JSON template as a parameter.  Any `null` value will trigger prompting on the console.  Input is not masked or muted, so you may want to run a clear-screen after to keep reduce the amount of time it is in the console buffer.

1. Pick a authorization method to use (`coinbase.oauth2`, `coinbase.v2_api`, `coinbase.v3_api`)
2. Fill in your template data, leave `null` values for prompting (ex: `coinbase_oauth2.json`)
3. Run the `update_keystore` command to prompt and encrypt secrets

Template:

```
{
  "format": "json",
  "coinbase": {
    "oauth2": {
      "auth_url": "https://api.coinbase.com/oauth/authorize",
      "token_url": "https://api.coinbase.com/oauth/token",
      "revoke_url": "https://api.coinbase.com/oauth/revoke",
      "redirect_url": "http://localhost:8000/callback",
      "scope": "wallet:user:read,wallet:accounts:read",
      "id": null,
      "secret": null
    }
  }
}
```

With both the GnuPG and OAuth2 templates, the `update_keystore` call will prompt for the `null` fields, and encrypt the resultant merge with GnuPG

```
pyexch --keystore gnupg_ks.json --params coinbase_oauth2.json --call update_keystore
```

If you choose OAuth2, you will need to create / authorize your app to get a grant token

```
pyexch --keystore gnupg_ks.json --auth coinbase.oauth2 --uri https://api.coinbase.com/oauth/authorize
```

This will launch your web-browser and web-server to service the request and store the keys in your keystore.  Note that since this get takes secret params, the `auth_url` is treated special and the parameters are built internally for processing to avoid the need for an encrypted `params.json` file.

You can display the keys that got updated on console using `print_keystore` call.  A redaction template can be included in `--params` to mask secrets from getting shown on screen.  In this workflow, simply seeing that the new oauth store got a auth token and a refresh token is a good indication that the calls worked.  If you want to see all the secrets, just omit the `--params` field in the call to `print_keystore`

```
pyexch --keystore gnupg_ks.json --params redactions.json5 --call print_keystore
```

Note that since OAuth tokens are short lived, you will need to refresh the tokens about every hour.  To refresh to token post to the `token_url` to get a new token.  Since this get takes secret params, the `token_url` is treated special and the parameters are built internally for processing to avoid the need for an encrypted `params.json` file.

```
pyexch --keystore gnupg_ks.json --method post --uri https://api.coinbase.com/oauth/token
```
Note: The `--auth` choice is cached in the keystore so the last choice used is assumed unless `--auth` is named again.

## Making REST or Client calls

Once you have good API / AUTH tokens stored, you can start making calls to the API's or Clients directly.  To determine which URLs are supported look at the [API V2][a] documentation, and [API V3][b] documentation.  Note that OAuth2 works on both v2 and v3 URLs.

To learn which calls are supported, look at the [V2 Client][c] and [V3 Client][d].  All parameters needed for the call commands are taken from the JSON file pointed to in the `--params` argument.

For example, to exercise the V2-API [Show Authorization Information endpoint][e], you can do the following

```
pyexch --keystore gnupg_ks.json --url https://api.coinbase.com/v2/user/auth
```

To call the [get_buy_price][p] method from the V2-Client using BTC-USD trading pair (use `\"` with echo on certain shells)

```
echo {"currency_pair" : "BTC-USD"} > params.json
pyexch --keystore gnupg_ks.json --params params.json --call get_buy_price
```

## Supported Call Endpoints

These are the supported options for the `--call` parameter

### Internal call endpoints

These are the call endpoints that have internal functions without exchange interaction

- `my_ipv4` - Display your external IPv4 address for API binding
- `my_ipv6` - Display your external IPv6 address for API binding
- `new_uuid` - Display a new UUID used for some API calls
- `update_keystore` - Used to modify an encrypted keystore (see above)
- `print_keystore` - Print the decrypted keystore to the console (with redactions)
- `sort_keystore` - Sort the keystore based on template provided in params
- `sort_keyfile` - Sort the keyfile based on template provided in params

### coinbase.oauth2 call endpoints

These endpoints are supported when using the `--auth` value of `coinbase.oauth2`.  These are exposed from the [coinbase.wallet.client.OAuthClient][h] client object.

- `refresh` - Refresh the Oauth2 tokens since they are short lived
- `revoke` - Revoke the existing Oauth2 token before expiration <!-- todo: test revocation more -->

### coinbase.oauth2 / coinbase.v2_api call endpoints

These endpoints are supported when using the `--auth` value of either `coinbase.oauth2` or `coinbase.v2_api`.  These are exposed from the [coinbase.wallet.client.OAuthClient][h] and [coinbase.wallet.client.Client][i] client objects.  All of these calls accept named parameters pulled from --params JSON.

- `_get` - Private client method that passes directly through to [requests object][j].
- `_post` - Private client method that passes directly through to [requests object][j]. 
- `_put` - Private client method that passes directly through to [requests object][j].
- `_delete` - Private client method that passes directly through to [requests object][j].
- `buy` -See [client documentation][k] for details.
- `cancel_request` -See [client documentation][k] for details.
- `commit_buy` -See [client documentation][k] for details.
- `commit_deposit` -See [client documentation][k] for details.
- `commit_sell` -See [client documentation][k] for details.
- `commit_withdrawal` -See [client documentation][k] for details.
- `complete_request` -See [client documentation][k] for details. 
- `create_account` -See [client documentation][k] for details.
- `create_address` -See [client documentation][k] for details.
- `create_checkout` -See [client documentation][k] for details.
- `create_checkout_order` -See [client documentation][k] for details.
- `create_order` -See [client documentation][k] for details.
- `create_report` -See [client documentation][k] for details.
- `delete_account` -See [client documentation][k] for details.
- `deposit` -See [client documentation][k] for details.
- `get_account` -See [client documentation][k] for details.
- `get_accounts` -See [client documentation][k] for details.
- `get_address` -See [client documentation][k] for details.
- `get_address_transactions` -See [client documentation][k] for details. 
- `get_addresses` -See [client documentation][k] for details.
- `get_auth_info` -See [client documentation][k] for details.
- `get_buy` -See [client documentation][k] for details.
- `get_buy_price` -See [client documentation][k] for details.
- `get_buys` -See [client documentation][k] for details.
- `get_checkout` -See [client documentation][k] for details.
- `get_checkout_orders` -See [client documentation][k] for details.
- `get_checkouts` -See [client documentation][k] for details.
- `get_currencies` -See [client documentation][k] for details.
- `get_current_user` -See [client documentation][k] for details.
- `get_deposit` -See [client documentation][k] for details.
- `get_deposits` -See [client documentation][k] for details. 
- `get_exchange_rates` -See [client documentation][k] for details.
- `get_historic_prices` -See [client documentation][k] for details.
- `get_merchant` -See [client documentation][k] for details.
- `get_notification` -See [client documentation][k] for details.
- `get_notifications` -See [client documentation][k] for details.
- `get_order` -See [client documentation][k] for details.
- `get_orders` -See [client documentation][k] for details.
- `get_payment_method` -See [client documentation][k] for details.
- `get_payment_methods` -See [client documentation][k] for details.
- `get_primary_account` -See [client documentation][k] for details.
- `get_report` -See [client documentation][k] for details.
- `get_reports` -See [client documentation][k] for details. 
- `get_sell` -See [client documentation][k] for details.
- `get_sell_price` -See [client documentation][k] for details.
- `get_sells` -See [client documentation][k] for details.
- `get_spot_price` -See [client documentation][k] for details.
- `get_time` -See [client documentation][k] for details.
- `get_transaction` -See [client documentation][k] for details.
- `get_transactions` -See [client documentation][k] for details.
- `get_user` -See [client documentation][k] for details.
- `get_withdrawal` -See [client documentation][k] for details.
- `get_withdrawals` -See [client documentation][k] for details.
- `refund_order` -See [client documentation][k] for details.
- `request_money` -See [client documentation][k] for details.
- `resend_request` -See [client documentation][k] for details.
- `sell` -See [client documentation][k] for details.
- `send_money` -See [client documentation][k] for details.
- `session` -See [client documentation][k] for details.
- `set_primary_account` -See [client documentation][k] for details.
- `transfer_money` -See [client documentation][k] for details.
- `update_account` -See [client documentation][k] for details.
- `update_current_user` -See [client documentation][k] for details.
- `verify_callback` -See [client documentation][k] for details. 
- `withdraw` -See [client documentation][k] for details.

### coinbase.v3_api call endpoints

These endpoints are supported when using the `--auth` value of `coinbase.v3_api`.  These are exposed from the [coinbase.rest.RESTClient][l]  client object.  All of these calls accept named parameters pulled from --params JSON.

- `get` - Public client method that passes directly through to [requests object][j].
- `post` - Public client method that passes directly through to [requests object][j].
- `put` - Public client method that passes directly through to [requests object][j].
- `delete` - Public client method that passes directly through to [requests object][j].
- `allocate_portfolio` -See [client documentation][m] for details.
- `cancel_orders` -See [client documentation][m] for details.
- `cancel_pending_futures_sweep` -See [client documentation][m] for details.
- `commit_convert_trade` -See [client documentation][m] for details.
- `create_convert_quote` -See [client documentation][m] for details.
- `create_order` -See [client documentation][m] for details.
- `create_portfolio` -See [client documentation][m] for details.
- `delete_portfolio` -See [client documentation][m] for details.
- `edit_order` -See [client documentation][m] for details.
- `edit_portfolio` -See [client documentation][m] for details.
- `get_account` -See [client documentation][m] for details.
- `get_accounts` -See [client documentation][m] for details.
- `get_best_bid_ask` -See [client documentation][m] for details.
- `get_candles` -See [client documentation][m] for details.
- `get_convert_trade` -See [client documentation][m] for details.
- `get_fills` -See [client documentation][m] for details.
- `get_futures_balance_summary` -See [client documentation][m] for details.
- `get_futures_position` -See [client documentation][m] for details.
- `get_market_trades` -See [client documentation][m] for details.
- `get_order` -See [client documentation][m] for details.
- `get_payment_method` -See [client documentation][m] for details.
- `get_perps_portfolio_summary` -See [client documentation][m] for details.
- `get_perps_position` -See [client documentation][m] for details.
- `get_portfolio_breakdown` -See [client documentation][m] for details.
- `get_portfolios` -See [client documentation][m] for details.
- `get_product` -See [client documentation][m] for details.
- `get_product_book` -See [client documentation][m] for details.
- `get_products` -See [client documentation][m] for details.
- `get_transaction_summary` -See [client documentation][m] for details.
- `get_unix_time` -See [client documentation][m] for details.
- `limit_order_gtc` -See [client documentation][m] for details.
- `limit_order_gtc_buy` -See [client documentation][m] for details.
- `limit_order_gtc_sell` -See [client documentation][m] for details.
- `limit_order_gtd` -See [client documentation][m] for details.
- `limit_order_gtd_buy` -See [client documentation][m] for details.
- `limit_order_gtd_sell` -See [client documentation][m] for details.
- `limit_order_ioc` -See [client documentation][m] for details.
- `limit_order_ioc_buy` -See [client documentation][m] for details.
- `limit_order_ioc_sell` -See [client documentation][m] for details.
- `list_futures_positions` -See [client documentation][m] for details.
- `list_futures_sweeps` -See [client documentation][m] for details.
- `list_orders` -See [client documentation][m] for details.
- `list_payment_methods` -See [client documentation][m] for details.
- `list_perps_positions` -See [client documentation][m] for details.
- `market_order` -See [client documentation][m] for details.
- `market_order_buy` -See [client documentation][m] for details.
- `market_order_sell` -See [client documentation][m] for details.
- `move_portfolio_funds` -See [client documentation][m] for details.
- `preview_edit_order` -See [client documentation][m] for details.
- `preview_limit_order_gtc` -See [client documentation][m] for details.
- `preview_limit_order_gtc_buy` -See [client documentation][m] for details.
- `preview_limit_order_gtc_sell` -See [client documentation][m] for details.
- `preview_limit_order_gtd` -See [client documentation][m] for details.
- `preview_limit_order_gtd_buy` -See [client documentation][m] for details.
- `preview_limit_order_gtd_sell` -See [client documentation][m] for details.
- `preview_limit_order_ioc` -See [client documentation][m] for details.
- `preview_limit_order_ioc_buy` -See [client documentation][m] for details.
- `preview_limit_order_ioc_sell` -See [client documentation][m] for details.
- `preview_market_order` -See [client documentation][m] for details.
- `preview_market_order_buy` -See [client documentation][m] for details.
- `preview_market_order_sell` -See [client documentation][m] for details.
- `preview_order` -See [client documentation][m] for details.
- `preview_stop_limit_order_gtc` -See [client documentation][m] for details.
- `preview_stop_limit_order_gtc_buy` -See [client documentation][m] for details.
- `preview_stop_limit_order_gtc_sell` -See [client documentation][m] for details.
- `preview_stop_limit_order_gtd` -See [client documentation][m] for details.
- `preview_stop_limit_order_gtd_buy` -See [client documentation][m] for details.
- `preview_stop_limit_order_gtd_sell` -See [client documentation][m] for details.
- `schedule_futures_sweep` -See [client documentation][m] for details.
- `stop_limit_order_gtc` -See [client documentation][m] for details.
- `stop_limit_order_gtc_buy` -See [client documentation][m] for details.
- `stop_limit_order_gtc_sell` -See [client documentation][m] for details.
- `stop_limit_order_gtd` -See [client documentation][m] for details.
- `stop_limit_order_gtd_buy` -See [client documentation][m] for details.
- `stop_limit_order_gtd_sell` -See [client documentation][m] for details.

<!-- Link Nest -->

[a]: https://docs.cloud.coinbase.com/sign-in-with-coinbase (api v2)
[b]: https://docs.cloud.coinbase.com/advanced-trade-api (api v3)
[c]: https://github.com/coinbase/coinbase-python/blob/master/README.rst#usage (client v2)
[d]: https://coinbase.github.io/coinbase-advanced-py/coinbase.rest.html#module-coinbase.rest.accounts (client v3)
[e]: https://docs.cloud.coinbase.com/sign-in-with-coinbase/docs/api-users#show-authorization-information
[f]: https://github.com/coinbase/coinbase-python#usage
[g]: https://github.com/Kijewski/pyjson5 (JSON5)
[h]: https://github.com/coinbase/coinbase-python/?tab=readme-ov-file#oauth2
[i]: https://github.com/coinbase/coinbase-python/?tab=readme-ov-file#api-key--secret
[j]: https://docs.python-requests.org/en/latest/api/
[k]: https://github.com/coinbase/coinbase-python/?tab=readme-ov-file#usage
[l]: https://coinbase.github.io/coinbase-advanced-py/coinbase.rest.html#restclient-constructor
[m]: https://coinbase.github.io/coinbase-advanced-py/index.html
[n]: https://stackoverflow.com/a/21928790/4634229
[o]: https://stackoverflow.com/a/48175912/4634229
[p]: https://github.com/coinbase/coinbase-python/?tab=readme-ov-file#market-data
