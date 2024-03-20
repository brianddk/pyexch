if __package__:
    from .keystore import Keystore
else:
    from keystore import Keystore    

from coinbase.wallet.client import Client, OAuthClient  # coinbase_v2
from coinbase.rest import RESTClient                    # coinbase_v3
from json import dumps, loads
from requests.auth import AuthBase
from requests.models import Response, PreparedRequest
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from functools import partial
import webbrowser, hmac, hashlib, time, requests

MINUTE = 60 # seconds

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
        msg = f"Params = '{self.exch._params}'"
        self.wfile.write(msg.encode('utf-8'))

class CbV2Auth(AuthBase):
    def __init__(self, api_key, secret_key):
        self.api_key = api_key
        self.secret_key = secret_key

    def __call__(self, request):
        timestamp = str(int(time.time()))
        message = timestamp + request.method + request.path_url + (request.body or '')
        signature = hmac.new(self.secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()

        request.headers.update({
            'CB-ACCESS-SIGN': signature,
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-ACCESS-KEY': self.api_key,
            'CB-VERSION': '2024-03-12',
            'Content-Type': 'application/json',
        })
        
        return request
        
class CbOa2Auth(AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, request):
        timestamp = str(int(time.time()))

        request.headers.update({
            'CB-ACCESS-TIMESTAMP': timestamp,
            'CB-VERSION': '2024-03-12',
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + self.token,
        })
        
        return request
        
class Exchange():
    def __init__(self, keystore):
        self.keystore = keystore
        self._params = None
        self._response = None

    def my_ipv4(self):
        return requests.get("https://v4.ident.me/").content.decode()
        
    def my_ipv6(self):
        return requests.get("https://v6.ident.me/").content.decode()

class Coinbase(Exchange):
    def __init__(self, keystore):
        super().__init__(keystore)
        
        self._oa2_auth_handler = partial(CbOaAuthHandler, self)
        
        if keystore.get('default') == 'coinbase.v2_api':
            self.v2_client = Client(
                keystore.get('coinbase.v2_api.key'),
                keystore.get('coinbase.v2_api.secret')
            )

            self.v2_req_auth = CbV2Auth(
                keystore.get('coinbase.v2_api.key'),
                keystore.get('coinbase.v2_api.secret')
            )

        elif keystore.get('default') == 'coinbase.oauth2' and self.keystore.get('coinbase.oauth2.token') and self.keystore.get('coinbase.oauth2.refresh'):
            self.oa2_client = OAuthClient(
                self.keystore.get('coinbase.oauth2.token'), 
                self.keystore.get('coinbase.oauth2.refresh')
            )

            self.oa2_req_auth = CbOa2Auth(
                self.keystore.get('coinbase.oauth2.token'),
            )

        elif keystore.get('default') == 'coinbase.v3_api':
            self.v3_client = RESTClient(
                api_key = self.keystore.get('coinbase.v3_api.key'), 
                api_secret = self.keystore.get('coinbase.v3_api.secret'),
            )

    def get(self, uri, params = None):
        self._response = None
        pth = uri.replace('https://api.coinbase.com', '')
        if params:
            self._params = data_toDict(params)
        if self.keystore.get('default') == 'coinbase.oauth2':
            if uri == self.keystore.get('coinbase.oauth2.auth_url'):
                self._response = self.oa2_auth() 
            else:
                self._response = self.oa2_refresh() 
                self._response = self.oa2_client._get(pth, params=params)
        elif self.keystore.get('default') == 'coinbase.v2_api':    
            self._response = self.v2_client._get(pth, params=params)
        elif self.keystore.get('default') == 'coinbase.v3_api':
            self._response = self.v3_client.get(pth, params=params)
        else:
            print("todo unknown get") # todo unknown get
            
        return data_toDict(self._response)
        
    def post(self, uri, params = None):
        data = params
        self._response = None
        pth = uri.replace('https://api.coinbase.com', '')
        if data:
            self._params = data_toDict(data)
        if self.keystore.get('default') == 'coinbase.oauth2':
            if uri == self.keystore.get('coinbase.oauth2.token_url'):
                self._response = self.oa2_refresh(force = True)
            elif uri == self.keystore.get('coinbase.oauth2.revoke_url'):
                self._response = self.oa2_revoke()
            else:
                self._response = self.oa2_refresh() 
                self._response = self.oa2_client._post(pth, data=data)
        elif self.keystore.get('default') == 'coinbase.v2_api':    
            self._response = self.v2_client._post(pth, data=data)
        elif self.keystore.get('default') == 'coinbase.v3_api':
            self._response = self.v3_client.post(pth, data=data)
        else:
            print("todo unknown post") # todo unknown get
            
        return data_toDict(self._response)
        
    def _raw_get(self, uri, params = None):
        self._response = None
        if params:
            self._params = data_toDict(params)
        if self.keystore.get('default') == 'coinbase.oauth2':
            if uri == self.keystore.get('coinbase.oauth2.auth_url'):
                self._response = self.oa2_auth() 
            else:
                self._response = self.oa2_refresh() 
                self._response = requests.get(uri, auth=self.oa2_req_auth, params=params)
        elif self.keystore.get('default') == 'coinbase.v2_api':    
            self._response = requests.get(uri, auth=self.v2_req_auth, params=params)
        elif self.keystore.get('default') == 'coinbase.v3_api':
            print("todo v3_api get fix") # Add some v3 get code
        else:
            print("todo unknown get") # todo unknown get
            
        return data_toDict(self._response)
        
    def oa2_auth(self):  
        # https://stackoverflow.com/a/49957974/4634229
        self._params = dict(
            response_type = 'code', 
            client_id = self.keystore.get('coinbase.oauth2.id'),
            scope = self.keystore.get('coinbase.oauth2.scope'),
        )
        # rule  https://forums.coinbasecloud.dev/t/walletsend-is-limited-1-00-day-per-user/866/2
        # broke https://forums.coinbasecloud.dev/t/oauth-application-maximum-of-1-00-per-month/7096/13
        if 'wallet:transactions:send' in self.keystore.get('coinbase.oauth2.scope'):
            self._params.update({
                'meta[send_limit_amount]'   : 1,
                'meta[send_limit_currency]' : 'USD',
                'meta[send_limit_period]'   : 'day'
            })
        req = PreparedRequest()
        req.prepare_url(self.keystore.get('coinbase.oauth2.auth_url'), self._params)
                
        # print("todo: ", uri)
        webbrowser.open(req.url)
        assert self.keystore.get('coinbase.oauth2.redirect_url').split(':')[1] == "//localhost"
        port = self.keystore.get('coinbase.oauth2.redirect_url').split(':')[2].split('/')[0]

        # _oa2_auth_handler holds a pointer to Exchange.self to modify self._params
        # Blocking call waiting for server to handle one request
        run_server(int(port), self._oa2_auth_handler)
        qparams = self._params
        # print(qparams)
        # self.keystore.set('coinbase.oauth2.login_identifier', qparams['login_identifier'][0])
        # self.keystore.set('coinbase.oauth2.state', qparams['state'][0])
        uri = self.keystore.get('coinbase.oauth2.token_url')
        self._params = dict(
            grant_type = "authorization_code",
            code = qparams['code'][0],
            client_id     = self.keystore.get('coinbase.oauth2.id'),
            client_secret = self.keystore.get('coinbase.oauth2.secret'),
            redirect_uri  = self.keystore.get('coinbase.oauth2.redirect_url')
        )
        # self.keystore.print()
        # print(dumps(params, indent=2))
        self._response = requests.post(uri, data=self._params)
        if self._response:
            data = self._response.json()
            self.keystore.set('coinbase.oauth2.expiration', data["expired_at"])
            self.keystore.set('coinbase.oauth2.token', data["access_token"])
            self.keystore.set('coinbase.oauth2.refresh', data["refresh_token"])
            # self.keystore.print()
            self.keystore.save()
        else:
            print(self._response)
            
        return data_toDict(self._response)

    def oa2_refresh(self, force = False):
        utime = time.time()
        if int(self.keystore.get('coinbase.oauth2.expiration')) - utime > MINUTE and not force:
            return dict() # no need to refresh, not forced
        uri = self.keystore.get('coinbase.oauth2.token_url')
        self._params = dict(
            grant_type = "refresh_token",
            client_id     = self.keystore.get('coinbase.oauth2.id'),
            client_secret = self.keystore.get('coinbase.oauth2.secret'),
            refresh_token = self.keystore.get('coinbase.oauth2.refresh')
        )
        self._response = requests.post(uri, data=self._params)
        if self._response:
            data = self._response.json()
            self.keystore.set('coinbase.oauth2.expiration', data["expired_at"])
            self.keystore.set('coinbase.oauth2.token', data["access_token"])
            self.keystore.set('coinbase.oauth2.refresh', data["refresh_token"])
            self.oa2_client.access_token = data["access_token"]
            self.oa2_client.refresh_token = data["refresh_token"]
            self.keystore.save()
        else:
            print(self._response)
        
        return data_toDict(self._response)
        
    def oa2_revoke(self):
        # broke? https://forums.coinbasecloud.dev/t/did-oauth2-revoke-uri-stop-doing-work/7394
        uri = self.keystore.get('coinbase.oauth2.revoke_url')
        self._params = dict(
            token = self.keystore.get('coinbase.oauth2.token'),
        )
        self._response = requests.post(uri, data=self._params)
        print(self._response)
        
        return data_toDict(self._response)
        

def run_server(port, handler):
    server_address = ('', port)
    httpd = HTTPServer(server_address, handler)
    print(f"Server listening on port {port}...")
    httpd.handle_request()
        
def create(keystore_json, default = None):
    keystore = Keystore(keystore_json)
    if default:
        keystore.set('default', default)
    
    if keystore.get('default'):
        default = keystore.get('default')
    
    if default and default.split('.')[0] == 'coinbase' or keystore.get('coinbase'):
        return Coinbase(keystore)
    else:
        pass # todo Throw exception

            
def data_toDict(data):
    if type(data) is dict:
        return data
    if type(data) is Response:
        try: 
            return data.json()
        except:
            return dict()
    if type(data) is str:
        try:
            return loads(data)
        except:
            return dict()
