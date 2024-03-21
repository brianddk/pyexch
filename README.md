# pyexch

***EARLY PREVIEW RELEASE*** of a rudimentary python CLI based rest client for Coinbase

```
usage: pyexch [-h] [--method <get,post,>] [--url https://...]
              [--params params.json] [--call get_accounts] --keystore ks.json
              [--auth exch.auth]

Python Exchange CLI (pyexch)

optional arguments:
  -h, --help            show this help message and exit
  --method <get,post,>  rest http method (get<default>,post,put,delete)
  --url https://...     rest http url to perform actions upon
  --params params.json  json / json5 filename holding rest parameters / data
  --call get_accounts   call method in the default client
  --keystore ks.json    json / json5 filename where secrets are stored
                        (backup!)
  --auth exch.auth      the auth method to use from keystore.

NOTE: Must name either "--call" or "--url", but not both
```

## Future Plans

- [x] Add GET and POST methods for Coinbase
- [x] Add OAuth2, API_v2 and API_v3 support for Coinbase
- [x] Tag a (beta) release to reduce the nead to use the HEAD
- [x] Release to PyPi for better CDN support
- [x] Use [JSON5][g] for `load` and `loads` operations
- [ ] Add PUT and DELETE methods for Coinbase
- [ ] Add Kraken as a supported Exchange
- [ ] Add Binance as a supported Exchange (from USA ?!?)
- [ ] Mask input on private data so it's is muted on screen

## Install and Initial Setup

This utility allows you to use a Cryptocurrency Exchange's REST API to perform basic tasks and retrieve current and historical account data.  You will need to setup API / OAuth2 access keys in your account to use this utility.  The utility supports both GPG and Trezor-CipherKeyValue encryption.  You will need either a GPG key pair installed, or a Trezor attached.  As a fallback you can store API keys in naked JSON, but that is obviously not recommended.

### Install with GIT / PIP

1. Get source: `git clone https://github.com/brianddk/pyexch.git`
2. Switch directories: `cd pyexch`
3. Install via pip: `pip install .`
4. Verify install (cli-mode): `pyexch --help`

Alternatively you can run it in module mode (`python -m pyexch --help`) or run the script directly (`python pyexch.py --help`).

### Install without GIT

To install the most recent edition directly from GitHub tarball:

```
pip install https://github.com/brianddk/pyexch/archive/refs/heads/main.tar.gz
```

You won't get to documentation or templates, but all the code will land and function 

### Install last release from PIP

1. Install: `pip install pyexch`
2. Verify install: `pyexch --help`

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
      "revoke_url": "https://api.coinbase.com/oauth/token",
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
pyexch --call update_keystore --params coinbase_oauth2.json --keystore gnupg_ks.json --auth coinbase.oauth2
```

If you choose OAuth2, you will need to create / authorize your app to get a grant token

```
pyexch --uri https://www.coinbase.com/oauth/authorize --keystore gnupg_ks.json --auth coinbase.oauth2
```

This will launch your web-browser and web-server to service the request and store the keys in your keystore.  You can display the keys on console using `print_keystore` call.  Note that since this get takes secret params, the `auth_url` is treated special and the parameters are built internally for processing to avoid the need for an encrypted `params.json` file.

```
pyexch --call print_keystore --keystore gnupg_ks.json
```

Note that since OAuth tokens are short lived, you will need to refresh the tokens about every hour.  To refresh to token post to the `token_url` to get a new token.  Note that since this get takes secret params, the `token_url` is treated special and the parameters are built internally for processing to avoid the need for an encrypted `params.json` file.

```
pyexch --method post --uri https://api.coinbase.com/oauth/token --keystore gnupg_ks.json
```
Note: The `--auth` choice is cached in the keystore so the last choice used is assumed unless `--auth` is named again.

## Making REST or Client calls

Once you have good API / AUTH tokens stored, you can start making calls to the API's or Clients directly.  To determine which URLs are supported look at the [API V2][a] documentation, and [API V3][b] documentation.  Note that OAuth2 works on both v2 and v3 URLs.

To learn which calls are supported, look at the [V2 Client][c] and [V3 Client][d].  All parameters needed for the call commands are taken from the JSON file pointed to in the `--params` argument.

For example, to exercise the V2-API [Show Authorization Information endpoint][e], you can do the following

```
pyexch --url https://api.coinbase.com/v2/user/auth --keystore gnupg_ks.json
```

To call the [get_buy_price][] method from the V2-Client using BTC-USD trading pair (use `\"` with echo on certain shells)

```
echo {"currency_pair" : "BTC-USD"} > params.json
pyexch --call get_buy_price --params params.json --keystore gnupg_ks.json
```

[a]: https://docs.cloud.coinbase.com/sign-in-with-coinbase (api v2)
[b]: https://docs.cloud.coinbase.com/advanced-trade-api (api v3)
[c]: https://github.com/coinbase/coinbase-python/blob/master/README.rst#usage (client v2)
[d]: https://coinbase.github.io/coinbase-advanced-py/coinbase.rest.html#module-coinbase.rest.accounts (client v3)
[e]: https://docs.cloud.coinbase.com/sign-in-with-coinbase/docs/api-users#show-authorization-information
[f]: https://github.com/coinbase/coinbase-python#usage
[g]: https://github.com/Kijewski/pyjson5 (JSON5)
