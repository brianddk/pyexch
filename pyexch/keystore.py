from base64 import b64decode, b64encode
from collections.abc import Mapping

# from os import environ
# from sys import stderr
from copy import deepcopy
from json import dump, dumps
from random import getrandbits
from subprocess import run
from zlib import compress, crc32, decompress

from pyjson5 import load, loads
from trezorlib.btc import get_public_node
from trezorlib.client import TrezorClient
from trezorlib.misc import decrypt_keyvalue, encrypt_keyvalue
from trezorlib.tools import parse_path
from trezorlib.transport import get_transport
from trezorlib.ui import ClickUI

# Convert to Munch: https://stackoverflow.com/a/24852544/4634229


class NoPassphraseUI(ClickUI):
    def get_passphrase(self, available_on_device=False) -> str:
        return ""


class Keystore:
    def __init__(self, keystore_json=None):
        self._tzclient = None
        self.closed = False
        self._filename = None
        self._keystore = None
        if keystore_json:
            self.load(keystore_json)

    # def __del__(self):
    # if self._dirty:
    # self.save() # Todo this hangs for some reason

    def get(self, field):
        obj = self._keystore
        for key in field.split("."):
            obj = obj.get(key)
            if not obj:
                break
        return obj

    def set(self, field, value):
        obj = self._keystore
        for key in field.split(".")[:-1]:
            obj[key] = obj.get(key, dict())
            obj = obj[key]
        obj[field.split(".")[-1]] = value
        self._dirty = True

    def delete(self, field):
        obj = self._keystore
        for key in field.split(".")[:-1]:
            obj = obj.get(key, dict())
        del obj[field.split(".")[-1]]
        self._dirty = True

    def close(self):
        self.closed = True
        self._filename = None
        if self._tzclient:
            self._tzclient.close()
            self._tzclient = None

    def save(self, force=False):
        if self._dirty is False and force is False:
            return

        assert not self.closed, "Can't save a closed keystore"

        if self._keyfile["format"] == "gnupg":
            recp = self._keyfile["gnupg"]["recipient"]

            proc = run(
                f"gpg --encrypt --recipient {recp} --armor".split(" "),
                input=dumps(self._keystore),
                capture_output=True,
                text=True,
            )

            # dict.json.gpg.asc
            self._keyfile["gnupg"]["enc_data"] = proc.stdout

        if self._keyfile["format"] == "trezor":
            self._opentz()

            ses = self._tzclient.session_id.hex()
            aod = self._keyfile["trezor"].get("ask_on_decrypt", True)
            aoe = self._keyfile["trezor"].get("ask_on_encrypt", False)
            self._keyfile["trezor"]["ask_on_decrypt"] = aod
            self._keyfile["trezor"]["ask_on_encrypt"] = aoe
            self._keyfile["trezor"]["last_session"] = ses
            path = parse_path(self._keyfile["trezor"].get("path"))
            key = self._keyfile["trezor"].get("key")
            node = get_public_node(self._tzclient, path)
            fgr = dword_to_hex(node.root_fingerprint)

            assert "zlib" == self._keyfile["trezor"].get("compression")
            if self._keyfile["trezor"].get("fingerprint"):
                assert fgr == self._keyfile["trezor"].get("fingerprint")
            self._keyfile["trezor"]["fingerprint"] = fgr

            # dict.json
            bdec = dumps(self._keystore, separators=(",", ":")).encode()
            self._keyfile["trezor"]["crc32"] = dword_to_hex(crc32(bdec))

            # dict.json.zlib
            zdec = compress(bdec)
            if "1" == self._tzclient.features.model:
                assert len(zdec) <= 1024, "Trezor-1 cipherkv buffer limit"
            else:
                assert len(zdec) <= 2048, "Trezor-T/3 cipherkv buffer limit"  # T can go to 8k, but IDK T3?

            # print("DBG: Length", len(zdec), )

            # dict.json.zlib.pad
            dec, pad = tz_pad(zdec)
            self._keyfile["trezor"]["hdr_padding"] = pad

            # dict.json.zlib.pad.cipherkv
            enc = encrypt_keyvalue(self._tzclient, path, key, dec, aoe, aod)

            # dict.json.zlib.pad.cipherkv.b64
            self._keyfile["trezor"]["enc_data"] = b64encode(enc).decode()

        if self._keyfile["format"] == "json":
            self._keyfile = self._keystore

        with open(self._filename, "w") as kf:
            dump(self._keyfile, kf, indent=2)

        self._dirty = False

    def load(self, keystore_json):
        with open(keystore_json, "r") as kf:
            self._keyfile = load(kf)

        self._filename = keystore_json
        if self._keyfile["format"] == "gnupg":
            if self._keyfile["gnupg"].get("enc_data"):
                proc = run(
                    "gpg --decrypt".split(" "),
                    input=self._keyfile["gnupg"]["enc_data"],
                    capture_output=True,
                    text=True,
                )
                keystore = loads(proc.stdout)
            else:
                keystore = dict()

        if self._keyfile["format"] == "trezor":
            if self._keyfile["trezor"].get("enc_data"):
                self._opentz()
                aod = self._keyfile["trezor"].get("ask_on_decrypt", True)
                aoe = self._keyfile["trezor"].get("ask_on_encrypt", False)
                path = parse_path(self._keyfile["trezor"].get("path"))

                # dict.json.zlib.pad.cipherkv.b64
                enc = b64decode(self._keyfile["trezor"].get("enc_data").encode())
                if "1" == self._tzclient.features.model:
                    assert len(enc) <= 1024, "Trezor-1 cipherkv buffer limit"
                else:
                    assert len(enc) <= 2048, "Trezor-T/3 cipherkv buffer limit"  # T can go to 8k, but IDK T3?

                key = self._keyfile["trezor"].get("key")
                node = get_public_node(self._tzclient, path)
                fgr = dword_to_hex(node.root_fingerprint)
                assert fgr == self._keyfile["trezor"].get("fingerprint")

                # dict.json.zlib.pad.cipherkv
                zdec = decrypt_keyvalue(self._tzclient, path, key, enc, aoe, aod)

                # dict.json.zlib.pad
                zdec = tz_strip(zdec, self._keyfile["trezor"].get("hdr_padding"))

                # dict.json.zlib
                dec = decompress(zdec)
                assert self._keyfile["trezor"].get("crc32") == dword_to_hex(crc32(dec))

                # dict.json
                keystore = loads(dec.decode())

            else:
                keystore = dict()

        if self._keyfile["format"] == "json":
            keystore = self._keyfile

        self._keystore = keystore
        self._dirty = False
        # end load()

    def print(self, template=None):
        if template:
            template = Keystore(template)
            bkup = Keystore()
            bkup._keystore = deepcopy(self._keystore)

            # The sorter has a byproduct of dropping the fields not in the second arg
            sorted = sort_dict(template._keystore, bkup._keystore)

            # Now that both dicts have the same keys, we can do a quite update to bkup
            update(bkup._keystore, sorted, ask=False)

            # Print bkup which is just self minus the redacted fields
            print(dumps(bkup._keystore, indent=2))
        else:
            print(dumps(self._keystore, indent=2))

    def update(self, ks_cls):
        self._keystore = update(self._keystore, ks_cls._keystore)
        self._dirty = True

    def _opentz(self):
        pen = self._keyfile["trezor"].get("passphrase_protection", False)
        pod = self._keyfile["trezor"].get("passphrase_on_device", False)
        ses = self._keyfile["trezor"].get("last_session")
        if ses:
            ses = bytes.fromhex(ses)
        if pen:
            ui = ClickUI(passphrase_on_host=not pod)
        else:
            ui = NoPassphraseUI()

        if not self._tzclient:
            transport = get_transport()
            self._tzclient = TrezorClient(transport, ui, ses)

        if pen:
            assert self._tzclient.features.passphrase_protection, "Passphrase requested in Keystore, but disabled on Trezor"

    def sort_keystore(self, json_file):
        self.save()
        with open(json_file, "r") as jf:
            template = load(jf)

        before_len = len(dumps(self._keystore))
        reordered_dict = sort_dict(self._keystore, template)
        after_len = len(dumps(reordered_dict))

        assert before_len == after_len, "The length changed after the sort, something is now missing"
        self._keystore = reordered_dict
        self.save(force=True)

    def sort_keyfile(self, json_file):
        self.save()
        with open(json_file, "r") as jf:
            template = load(jf)

        before_len = len(dumps(self._keyfile))
        reordered_dict = sort_dict(self._keyfile, template)
        after_len = len(dumps(reordered_dict))

        assert before_len == after_len, "The length changed after the sort, something is now missing"
        self._keyfile = reordered_dict
        self.save(force=True)


def tz_pad(zdec):
    pad = (16 - len(zdec) % 16) % 16
    filler = bytearray(getrandbits(8) for _ in range(pad))
    return (filler + zdec, pad)


def tz_strip(dec, pad):
    return dec[pad:]


def sort_dict(input_dict, template):
    if isinstance(input_dict, dict):
        reordered_dict = {}
        for key in template:
            if key in input_dict:
                reordered_dict[key] = sort_dict(input_dict[key], template[key])
        return reordered_dict
    else:
        return input_dict


def update(old_dict, new_dict, path="", ask=True):
    for key, val in new_dict.items():
        if isinstance(val, Mapping):
            old_dict[key] = update(old_dict.get(key, {}), val, f"{path}{key}.", ask)
        else:
            prompt = path + key
            if ask and val is None:
                val = input(f"Enter {prompt}: ")
                if prompt == "coinbase.v3_api.secret":
                    val = val.replace("\\n", "\n")
                if key == "auth_ips":
                    val = [ip.strip() for ip in val.split(",")]
            old_dict[key] = val

    return old_dict


def dword_to_hex(x):
    return ("0" * 8 + hex(x).replace("0x", ""))[-8:]


def hex_to_dword(x):
    return int(x, 16)
