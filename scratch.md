# RAW

py-exchange --method [get | post | delete] --url [url] --params [params.json] --keystore [filename.txt] --auth [coinbase.v2_key | coinbase.v3_key | coinbase.oauth2]
  - https://www.coinbase.com/oauth/authorize - starts an OAuth2 grant
  - https://www.coinbase.com/oauth/token - starts an OAuth2 refresh
  - Order of precidence per API v2: {oauth2, v2_key}, v3: {oauth2, v3_key}

# API

# https://jqlang.github.io/jq/manual/

py-exchange --call [endpoint] --params [params.json] --keystore [filename.txt]
  - exchange is implied from keystore which holds exchange name.
  - api_ver is implied from keystore which holds api version
  - auth_type is implied from keystore which holds it.

# Custom endpoints

- help (name keystore for v2 / v3 help)
    Display help text
- update_keystore --params [updates.json] --keystore [keystore.json.gnupg.asc | keystore.json.gzip.cipherkv]
    Any `null` field in updates.json will prompt the user@console for input
- print_keystore --params [redactions.json] --keystore [keystore.json.gnupg.asc | keystore.json.gzip.cipherkv]
    Any `null` field in redactions.json will produce a null on the print

https://v4.ident.me/
https://v6.ident.me/

v2: https://pypi.org/project/coinbase/
v3: https://pypi.org/project/coinbase-advanced-py/
https://stackoverflow.com/questions/63722558/different-python-packages-with-the-same-top-level-name
https://stackoverflow.com/questions/56907085/import-two-python-packages-with-the-same-name-for-use-in-the-same-project
https://stackoverflow.com/questions/78163953/load-two-different-python-packages-with-the-same-name-as-gracefully-as-possible

https://stackoverflow.com/a/41432835

https://github.com/Kijewski/pyjson5

Objects

Module pyexch

pyexch.__main__
    from .pyexch import main
    
    if __name__ == "__main__": main()

pyexch.pyexch
    main()

pyexch.pyexch.PyExch
    call()
    raw()
    exchange.

pyexch.keystore.KeyStore
d   load()
d   save()
d   update()
d   print()
?   close()
d   get()
d   set()
d   _keystore.
    
pyexch.exchange.Exchange
d   create()
    
d   Exchange
d     keystore.
    
    Kraken
    Coinbase
d     get()
      post()
d     oa2_auth()
d     oa2_refresh()
      call()
d     oa2_client.
      v2_client.
      v3_client.
      v3_rest.
d     oa2_req_auth.
d     v2_req_auth.

Make runnable as `python -m py-exchange` as well as getting a cli on `python -m pip install py-exchange`
    