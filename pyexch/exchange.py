if __package__:
    from .keystore import Keystore
else:
    from keystore import Keystore

import hashlib
import hmac
import time
import webbrowser
from functools import partial
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import requests
from coinbase.rest import RESTClient  # coinbase_v3
from coinbase.wallet.client import Client, OAuthClient  # coinbase_v2
from pyjson5 import loads  # , Json5DecoderException

# from json import dumps
# from requests import JSONDecodeError
from requests.auth import AuthBase
from requests.models import PreparedRequest, Response

MINUTE = 60  # seconds


# https://stackoverflow.com/a/52046062/4634229
class CbOaAuthHandler(BaseHTTPRequestHandler):
    def __init__(self, exch, *args, **kwargs):
        self.exch = exch
        super().__init__(*args, **kwargs)

    def do_GET(self):
        parsed_path = urlparse(self.path)
        self.exch._params = parse_qs(parsed_path.query)

        self.send_response(200)
        self.end_headers()

        msg = """
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
          "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
        <head>
            <meta charset="UTF-8" />
            <meta http-equiv="X-UA-Compatible" content="IE=edge" />
            <title>Redirecting to PyExch Github</title>
            <meta http-equiv="refresh" content="3; url=https://github.com/brianddk/pyexch" />
        </head>
        <body>
            <h1>Redirecting to github.com/brianddk/pyexch in 3... 2... 1...</h1>
        </body>
        </html>
        """

        self.wfile.write(msg.encode("utf-8"))

    # Mute the log to keep secrets off console
    def log_message(self, format, *args):
        return


class CbV2Auth(AuthBase):
    def __init__(self, api_key, secret_key):
        self.api_key = api_key
        self.secret_key = secret_key

    def __call__(self, request):
        timestamp = str(int(time.time()))
        message = timestamp + request.method + request.path_url + (request.body or "")
        signature = hmac.new(
            self.secret_key.encode(), message.encode(), hashlib.sha256
        ).hexdigest()

        request.headers.update(
            {
                "CB-ACCESS-SIGN": signature,
                "CB-ACCESS-TIMESTAMP": timestamp,
                "CB-ACCESS-KEY": self.api_key,
                "CB-VERSION": "2024-03-12",
                "Content-Type": "application/json",
            }
        )

        return request


class CbOa2Auth(AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, request):
        timestamp = str(int(time.time()))

        request.headers.update(
            {
                "CB-ACCESS-TIMESTAMP": timestamp,
                "CB-VERSION": "2024-03-12",
                "Content-Type": "application/json",
                "Authorization": "Bearer " + self.token,
            }
        )

        return request


class Exchange:

    @classmethod
    def create(cls, keystore_json, default=None):
        keystore = Keystore(keystore_json)
        if default:
            keystore.set("default", default)

        if keystore.get("default"):
            default = keystore.get("default")

        if default and default.split(".")[0] == "coinbase" or keystore.get("coinbase"):
            return Coinbase(keystore)
        else:
            return Exchange(keystore)

    def __init__(self, keystore):
        self.keystore = keystore
        self._params = None
        self._response = None

    def my_ipv4(self):
        return requests.get("https://v4.ident.me/").content.decode()

    def my_ipv6(self):
        return requests.get("https://v6.ident.me/").content.decode()

    def new_uuid(self):
        return uuid4()

    def dbg(self):
        token = self.keystore.get("coinbase.oauth2.token")
        return f"DBG: {token[:4]}...{token[-4:]}"

    def tick(self):
        import time

        expiration = self.keystore.get("coinbase.oauth2.expiration")
        left = expiration - time.time()
        hrs = left // (60 * 60)
        min = (left - hrs * 60 * 60) // 60
        sec = left - hrs * 60 * 60 - min * 60
        return f"DBG: countdown {int(hrs):02}:{int(min):02}:{sec:0>02.2f}"


class Coinbase(Exchange):
    def __init__(self, keystore):
        super().__init__(keystore)

        self._oa2_auth_handler = partial(CbOaAuthHandler, self)

        if (
            keystore.get("default") == "coinbase.v2_api"
            and keystore.get("coinbase.v2_api.key")
            and keystore.get("coinbase.v2_api.secret")
        ):
            self.v2_client = Client(
                keystore.get("coinbase.v2_api.key"),
                keystore.get("coinbase.v2_api.secret"),
            )

            self.v2_req_auth = CbV2Auth(
                keystore.get("coinbase.v2_api.key"),
                keystore.get("coinbase.v2_api.secret"),
            )

        elif (
            keystore.get("default") == "coinbase.oauth2"
            and keystore.get("coinbase.oauth2.token")
            and keystore.get("coinbase.oauth2.refresh")
        ):
            self.oa2_client = OAuthClient(
                keystore.get("coinbase.oauth2.token"),
                keystore.get("coinbase.oauth2.refresh"),
            )
            self._response = self.oa2_refresh()
            self._response = dict(msg="REDACTED") if self._response else self._response

            self.oa2_req_auth = CbOa2Auth(
                keystore.get("coinbase.oauth2.token"),
            )

        elif (
            keystore.get("default") == "coinbase.v3_api"
            and keystore.get("coinbase.v3_api.key")
            and keystore.get("coinbase.v3_api.secret")
        ):
            self.v3_client = RESTClient(
                api_key=keystore.get("coinbase.v3_api.key"),
                api_secret=keystore.get("coinbase.v3_api.secret"),
            )

    def get(self, uri, params=None):
        self._response = None
        trim_str = "https://api.coinbase.com"
        uri = uri.replace(trim_str, "")
        if params:
            self._params = data_toDict(params)
        if self.keystore.get("default") == "coinbase.oauth2":
            if trim_cmp(trim_str, uri, self.keystore.get("coinbase.oauth2.auth_url")):
                self._response = self.oa2_auth()
                self._response = (
                    dict(msg="REDACTED") if self._response else self._response
                )
            else:
                self._response = self.oa2_client._get(uri, params=params)
        elif self.keystore.get("default") == "coinbase.v2_api":
            self._response = self.v2_client._get(uri, params=params)
        elif self.keystore.get("default") == "coinbase.v3_api":
            self._response = self.v3_client.get(uri, params=params)
        else:
            print("todo unknown get")  # todo unknown get

        return data_toDict(self._response)

    def post(self, uri, params=None):
        data = params
        self._response = None
        trim_str = "https://api.coinbase.com"
        uri = uri.replace(trim_str, "")
        if data:
            self._params = data_toDict(data)
        if self.keystore.get("default") == "coinbase.oauth2":
            if trim_cmp(trim_str, uri, self.keystore.get("coinbase.oauth2.token_url")):
                self._response = self.oa2_refresh(force=True)
                self._response = (
                    dict(msg="REDACTED") if self._response else self._response
                )
            elif trim_cmp(
                trim_str, uri, self.keystore.get("coinbase.oauth2.revoke_url")
            ):
                self._response = self.oa2_revoke()
            else:
                self._response = self.oa2_client._post(uri, data=data)
        elif self.keystore.get("default") == "coinbase.v2_api":
            self._response = self.v2_client._post(uri, data=data)
        elif self.keystore.get("default") == "coinbase.v3_api":
            self._response = self.v3_client.post(uri, data=data)
        else:
            print("todo unknown post")  # todo unknown get

        return data_toDict(self._response)

    def put(self, uri, params=None):
        data = params
        self._response = None
        trim_str = "https://api.coinbase.com"
        uri = uri.replace(trim_str, "")
        if data:
            self._params = data_toDict(data)
        if self.keystore.get("default") == "coinbase.oauth2":
            self._response = self.oa2_client._put(uri, data=data)
        elif self.keystore.get("default") == "coinbase.v2_api":
            self._response = self.v2_client._put(uri, data=data)
        elif self.keystore.get("default") == "coinbase.v3_api":
            self._response = self.v3_client.put(uri, data=data)
        else:
            print("todo unknown post")  # todo unknown get

        return data_toDict(self._response)

    def delete(self, uri, params=None):
        self._response = None
        trim_str = "https://api.coinbase.com"
        uri = uri.replace(trim_str, "")

        # No CB endpoint is using params or data on delete
        #  If added back, remember to put it in the calls below.
        # data = params
        # if data:
        #   self._params = data_toDict(data)

        if self.keystore.get("default") == "coinbase.oauth2":
            self._response = self.oa2_client._delete(uri)
        elif self.keystore.get("default") == "coinbase.v2_api":
            self._response = self.v2_client._delete(uri)
        elif self.keystore.get("default") == "coinbase.v3_api":
            self._response = self.v3_client.delete(uri)
        else:
            print("todo unknown post")  # todo unknown get

        return data_toDict(self._response)

    def _raw_get(self, uri, params=None):
        self._response = None
        if params:
            self._params = data_toDict(params)
        if self.keystore.get("default") == "coinbase.oauth2":
            if uri == self.keystore.get("coinbase.oauth2.auth_url"):
                self._response = self.oa2_auth()
            else:
                self._response = requests.get(
                    uri, auth=self.oa2_req_auth, params=params
                )
        elif self.keystore.get("default") == "coinbase.v2_api":
            self._response = requests.get(uri, auth=self.v2_req_auth, params=params)
        elif self.keystore.get("default") == "coinbase.v3_api":
            print("todo v3_api get fix")  # Add some v3 get code
        else:
            print("todo unknown get")  # todo unknown get

        return data_toDict(self._response)

    def oa2_auth(self):
        # https://stackoverflow.com/a/49957974/4634229
        self._params = dict(
            response_type="code",
            client_id=self.keystore.get("coinbase.oauth2.id"),
            scope=self.keystore.get("coinbase.oauth2.scope"),
        )
        # rule  https://forums.coinbasecloud.dev/t/walletsend-is-limited-1-00-day-per-user/866/2
        # broke https://forums.coinbasecloud.dev/t/oauth-application-maximum-of-1-00-per-month/7096/13
        # Confirmed this meta tags allow to set the send limit.  Next is to try a send with CB-2FA-TOKEN
        # header: https://docs.cloud.coinbase.com/sign-in-with-coinbase/docs/sign-in-with-coinbase-2fa
        if "wallet:transactions:send" in self.keystore.get("coinbase.oauth2.scope"):
            self._params.update(
                {
                    "meta[send_limit_amount]": 1,
                    "meta[send_limit_currency]": "USD",
                    "meta[send_limit_period]": "day",
                }
            )
        req = PreparedRequest()
        req.prepare_url(self.keystore.get("coinbase.oauth2.auth_url"), self._params)

        webbrowser.open(req.url)
        assert (
            self.keystore.get("coinbase.oauth2.redirect_url").split(":")[1]
            == "//localhost"
        )
        port = (
            self.keystore.get("coinbase.oauth2.redirect_url")
            .split(":")[2]
            .split("/")[0]
        )

        # _oa2_auth_handler holds a pointer to Exchange.self to modify self._params
        # Blocking call waiting for server to handle one request
        run_server(int(port), self._oa2_auth_handler)
        qparams = self._params
        # print(qparams)
        # self.keystore.set('coinbase.oauth2.login_identifier', qparams['login_identifier'][0])
        # self.keystore.set('coinbase.oauth2.state', qparams['state'][0])
        uri = self.keystore.get("coinbase.oauth2.token_url")
        self._params = dict(
            grant_type="authorization_code",
            code=qparams["code"][0],
            client_id=self.keystore.get("coinbase.oauth2.id"),
            client_secret=self.keystore.get("coinbase.oauth2.secret"),
            redirect_uri=self.keystore.get("coinbase.oauth2.redirect_url"),
        )
        # self.keystore.print()
        # print(dumps(params, indent=2))
        self._response = requests.post(uri, data=self._params)
        if self._response:
            data = self._response.json()
            self.keystore.set("coinbase.oauth2.expiration", data["expired_at"])
            self.keystore.set("coinbase.oauth2.token", data["access_token"])
            self.keystore.set("coinbase.oauth2.refresh", data["refresh_token"])
            self.keystore.save()
        else:
            print(self._response)

        return data_toDict(self._response)

    def oa2_refresh(self, force=False):
        utime = time.time()
        if (
            int(self.keystore.get("coinbase.oauth2.expiration")) - utime > MINUTE
            and not force
        ):
            return dict()  # no need to refresh, not forced
        uri = self.keystore.get("coinbase.oauth2.token_url")
        self._params = dict(
            grant_type="refresh_token",
            client_id=self.keystore.get("coinbase.oauth2.id"),
            client_secret=self.keystore.get("coinbase.oauth2.secret"),
            refresh_token=self.keystore.get("coinbase.oauth2.refresh"),
        )
        self._response = requests.post(uri, data=self._params)
        if self._response:
            data = self._response.json()
            self.keystore.set("coinbase.oauth2.expiration", data["expired_at"])
            self.keystore.set("coinbase.oauth2.token", data["access_token"])
            self.keystore.set("coinbase.oauth2.refresh", data["refresh_token"])
            self.oa2_client.access_token = data["access_token"]
            self.oa2_client.refresh_token = data["refresh_token"]
            self.keystore.save()
        else:
            print(self._response)

        return data_toDict(self._response)

    def oa2_revoke(self):
        # todo: CVE broke? https://forums.coinbasecloud.dev/t/did-oauth2-revoke-uri-stop-doing-work/7394
        uri = self.keystore.get("coinbase.oauth2.revoke_url")
        self._params = dict(
            token=self.keystore.get("coinbase.oauth2.token"),
            client_id=self.keystore.get("coinbase.oauth2.id"),
            client_secret=self.keystore.get("coinbase.oauth2.secret"),
        )
        self._response = requests.post(uri, data=self._params)

        return data_toDict(self._response)


def run_server(port, handler):
    server_address = ("", port)
    httpd = HTTPServer(server_address, handler)
    print(f"Server listening on port {port}...")
    httpd.handle_request()


def data_toDict(data):
    # bugbug: This should never happen, but the cloudflare (or whoever) server sometimes returns
    # Requests.Response.content as <type 'str'> and other times as <type 'bytes'>.  This breaks
    # Requests.Response.json() since it expects 'bytes'
    # https://github.com/psf/requests/blob/d63e94f/src/requests/models.py#L942
    # https://github.com/brianddk/pyexch/issues/11
    if type(data) is dict:
        return data
    if type(data) is Response:
        if type(data.content) is str:
            data = data.content
        else:
            try:
                return data.json()
            except Exception:  # as e:
                return dict()
    if type(data) is str:
        try:
            return loads(data)
        except Exception:  # as e:
            return dict()


def trim_cmp(trim_str, str_a, str_b):
    str_a = str_a.replace(trim_str, "")
    str_b = str_b.replace(trim_str, "")
    return str_a == str_b
