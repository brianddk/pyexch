from pyjson5 import load, loads
from json import dump, dumps
from subprocess import run
from collections.abc import Mapping
from base64 import b64decode, b64encode
from zlib import compress, decompress, crc32
from random import getrandbits
from os import environ
from sys import stderr

from trezorlib.client import TrezorClient
from trezorlib.misc import decrypt_keyvalue, encrypt_keyvalue
from trezorlib.tools import parse_path
from trezorlib.transport import get_transport
from trezorlib.btc import get_public_node
from trezorlib.ui import ClickUI

dword_to_hex = lambda x: ('0' * 8 + hex(x).replace('0x', ''))[-8:]
hex_to_dword = lambda x: int(x, 16)

# Convert to Munch: https://stackoverflow.com/a/24852544/4634229

class NoPassphraseUI(ClickUI):
    def get_passphrase(self, available_on_device = False) -> str:
        return ""

class Keystore():
    def __init__(self, keystore_json = None):
        self._tzclient = None
        self.closed    = False
        self._keyfile  = None
        if(keystore_json):
            self.load(keystore_json)            
        
    # def __del__(self):
        # if self._dirty:
            # self.save() # Todo this hangs for some reason
        
    def get(self, field):
        obj = self._keystore
        for key in field.split('.'):
            obj = obj.get(key)
            if not obj: break
        return obj

    def set(self, field, value):
        obj = self._keystore
        for key in field.split('.')[:-1]:
            obj = obj.get(key, dict())
        obj[field.split('.')[-1]] = value
        self._dirty = True
        
    def delete(self, field):
        obj = self._keystore
        for key in field.split('.')[:-1]:
            obj = obj.get(key, dict())
        del obj[field.split('.')[-1]]
        self._dirty = True
        
    def close(self):
        self.closed = True
        self._keyfile = None
        if self._tzclient:
            self._tzclient.close()
            self._tzclient = None
                            
    def save(self, force = False):
        if self._dirty == False and force == False:
            return
            
        assert not self.closed, "Can't save a closed keystore"
        
        with open(self._keyfile, 'r') as kf:
            kf_dict = load(kf)
            
        if kf_dict['format'] == 'gnupg':
            recp = kf_dict['gnupg']['recipient']
            
            proc = run(f"gpg --encrypt --recipient {recp} --armor".split(' '), 
                input = dumps(self._keystore),
                capture_output=True,
                text = True,
            )

            # dict.json.gpg.asc
            kf_dict['gnupg']['enc_data'] = proc.stdout
        
        if kf_dict['format'] == 'trezor':
            self._opentz(kf_dict)
            
            ses = self._tzclient.session_id.hex()
            aod = kf_dict['trezor'].get('ask_on_decrypt', True)            
            aoe = kf_dict['trezor'].get('ask_on_encrypt', False)
            kf_dict['trezor']['ask_on_decrypt'] = aod
            kf_dict['trezor']['ask_on_encrypt'] = aoe
            kf_dict['trezor']['last_session'] = ses
            path = parse_path(kf_dict['trezor'].get('path'))
            key = kf_dict['trezor'].get('key')
            node = get_public_node(self._tzclient, path)
            fgr = dword_to_hex(node.root_fingerprint)

            assert 'zlib' == kf_dict['trezor'].get('compression')
            if kf_dict['trezor'].get('fingerprint'):
                assert fgr == kf_dict['trezor'].get('fingerprint')
            kf_dict['trezor']['fingerprint'] = fgr

            # dict.json
            bdec = dumps(self._keystore, separators=(',',':')).encode()
            kf_dict['trezor']['crc32'] = dword_to_hex(crc32(bdec))            
            
            # dict.json.zlib
            zdec = compress(bdec)
            assert len(zdec) <= 1024 # Trezor-1 cipherkv buffer limit
            
            # dict.json.zlib.pad
            dec, pad = tz_pad(zdec)
            kf_dict['trezor']['hdr_padding'] = pad
            
            # dict.json.zlib.pad.cipherkv
            enc = encrypt_keyvalue(self._tzclient, path, key, dec, aoe, aod)

            # dict.json.zlib.pad.cipherkv.b64
            kf_dict['trezor']['enc_data'] = b64encode(enc).decode()
        
        if kf_dict['format'] == 'json':
            kf_dict = self._keystore

        with open(self._keyfile, 'w') as kf:
            dump(kf_dict, kf, indent=2, sort_keys=True)
        
        self._dirty = False
    
    def load(self, keystore_json):
        with open(keystore_json, 'r') as kf:
            kf_dict = load(kf)

        self._keyfile = keystore_json
        if kf_dict['format'] == 'gnupg':
            if kf_dict['gnupg'].get('enc_data'):
                proc = run(f"gpg --decrypt".split(' '), 
                    input=kf_dict['gnupg']['enc_data'],
                    capture_output=True,
                    text = True,
                )
                keystore = loads(proc.stdout)
            else:
                keystore = dict()
        
        if kf_dict['format'] == 'trezor':
            if kf_dict['trezor'].get('enc_data'):
                self._opentz(kf_dict)
                aod = kf_dict['trezor'].get('ask_on_decrypt', True)            
                aoe = kf_dict['trezor'].get('ask_on_encrypt', False)
                path = parse_path(kf_dict['trezor'].get('path'))

                # dict.json.zlib.pad.cipherkv.b64
                enc = b64decode(kf_dict['trezor'].get('enc_data').encode())
                key = kf_dict['trezor'].get('key')
                node = get_public_node(self._tzclient, path)
                fgr = dword_to_hex(node.root_fingerprint)
                assert fgr == kf_dict['trezor'].get('fingerprint')

                # dict.json.zlib.pad.cipherkv
                zdec = decrypt_keyvalue(self._tzclient, path, key, enc, aoe, aod)
                
                # dict.json.zlib.pad
                zdec = tz_strip(zdec, kf_dict['trezor'].get('hdr_padding'))
                
                # dict.json.zlib
                dec = decompress(zdec)
                assert kf_dict['trezor'].get('crc32') == dword_to_hex(crc32(dec))
                
                # dict.json
                keystore = loads(dec.decode())

            else:
                keystore = dict()
        
        if kf_dict['format'] == 'json':
            keystore = kf_dict
        
        self._keystore = keystore
        self._dirty = False
    
    def print(self, show_private = True):
        # Todo enable show_private = False
        print(dumps(self._keystore, indent=2, sort_keys=True))

    def _update(self, old_obj, new_obj, path=""):
        for key, val in new_obj.items():
            if isinstance(val, Mapping):
                old_obj[key] = self._update(old_obj.get(key, {}), val, f"{path}{key}.")
            else:
                prompt = path+key
                if val == None:
                    val = input(f"Enter {prompt}: ")
                    if prompt == "coinbase.v3_api.secret":
                        val = val.replace("\\n", "\n")
                    if key == "auth_ips":
                        val = [ip.strip() for ip in val.split(',')]                
                old_obj[key] = val

        return old_obj
        
    def update(self, ks_cls):
        self._keystore = self._update(self._keystore, ks_cls._keystore)
        self._dirty = True
        
    def _opentz(self, kf_dict):
        pen = kf_dict['trezor'].get('passphrase_protection', False)
        pod = kf_dict['trezor'].get('passphrase_on_device', False)
        ses = kf_dict['trezor'].get('last_session')
        if ses: ses = bytes.fromhex(ses)
        if pen:
            ui = ClickUI(passphrase_on_host=not pod)
        else:
            ui = NoPassphraseUI()
            
        if not self._tzclient:
            transport = get_transport()
            self._tzclient = TrezorClient(transport, ui, ses)

        if pen:  
            assert self._tzclient.features.passphrase_protection , "Passphrase requested in Keystore, but disabled on Trezor"
    

def tz_pad(zdec):
    pad = (16 - len(zdec) % 16) % 16
    filler = bytearray(getrandbits(8) for _ in range(pad))
    return (filler + zdec, pad)

def tz_strip(dec, pad):
    return dec[pad:]