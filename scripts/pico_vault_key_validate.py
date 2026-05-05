#!/usr/bin/env python3
"""
Script to check that your recovered private key is correct.

Dependencies:
    pip install ecdsa bitcoinlib
"""

import argparse
import base64
import hashlib
import sys

from ecdsa import BadSignatureError, SECP256k1, SigningKey, VerifyingKey
from ecdsa.util import sigdecode_string, sigencode_string

def _sha256d(b: bytes) -> bytes:
    return hashlib.sha256(hashlib.sha256(b).digest()).digest()

def _varint(n: int) -> bytes:
    if n < 0xfd:
        return bytes([n])
    if n <= 0xffff:
        return b"\xfd" + n.to_bytes(2, "little")
    if n <= 0xffffffff:
        return b"\xfe" + n.to_bytes(4, "little")
    return b"\xff" + n.to_bytes(8, "little")

def bitcoin_message_hash(msg: bytes) -> bytes:
    prefix = b"\x18Bitcoin Signed Message:\n"
    return _sha256d(prefix + _varint(len(msg)) + msg)

def sign_message(priv: bytes, msg: bytes, compressed: bool = True) -> bytes:
    sk = SigningKey.from_string(priv, curve=SECP256k1)
    digest = bitcoin_message_hash(msg)
    rs = sk.sign_digest_deterministic(
        digest, hashfunc=hashlib.sha256, sigencode=sigencode_string)
    return rs

def verify_message_pubkey(pub: VerifyingKey, sig: bytes, msg: bytes) -> bool:
    digest = bitcoin_message_hash(msg)
    try:
        return pub.verify_digest(sig, digest, sigdecode=sigdecode_string)
    except BadSignatureError:
        return False

def parse_privkey_hex(hex: str) -> bytes:
    """
    Convert hexstring to bytes and do some checks.
    """
    raw = bytes.fromhex(hex)
    if len(raw) != 32:
        raise ValueError(f"private key must be 32 bytes, got {len(raw)}")
    n = int.from_bytes(raw, "big")
    if n == 0 or n >= SECP256k1.order:
        raise ValueError("private key is out of range for secp256k1")
    return raw

def load_pubkey_pem(path: str) -> VerifyingKey:
    with open(path, "rb") as f:
        vk = VerifyingKey.from_pem(f.read())
    if vk.curve != SECP256k1:
        raise ValueError(f"public key must be on secp256k1, got {vk.curve.name}")
    return vk

def main():
    ap = argparse.ArgumentParser(
        description="Use recovered private scalar to sign a message ")
    ap.add_argument("privkey_hex", help="32-byte secp256k1 private scalar in hex")
    ap.add_argument("pubkey_pem", help="Pubkey of the device")
    ap.add_argument("--message", default="key from the pico vault!",
                    help="Message to sign with the recovered key")
    args = ap.parse_args()

    priv = parse_privkey_hex(args.privkey_hex)
    pub_hex = None

    try:
        from bitcoinlib.keys import Key
        key         = Key(import_key=priv.hex(), network='testnet', compressed=True)
        wif         = key.wif()
        pub_hex     = key.public_hex
        addr_legacy = key.address()                                    # P2PKH
        addr_segwit = key.address(script_type="p2wpkh", encoding="bech32")  # P2WPKH
        print(f"=== Pico vault key bitcoint info ===")
        print(f"network                  : testnet")
        print(f"private key (hex)        : {priv.hex()}")
        print(f"private key (WIF)        : {wif}")
        print(f"public key (compressed)  : {pub_hex}")
        print(f"address (legacy / P2PKH) : {addr_legacy}")
        print(f"address (segwit / P2WPKH): {addr_segwit}")
    except ImportError:
        print(f"no bitloinlib available ")
    print()

    msg = args.message.encode()
    sig = sign_message(priv, msg, compressed=True)
    supplied = load_pubkey_pem(args.pubkey_pem)
    supplied_hex = supplied.to_string("compressed").hex()
    if pub_hex:
        matches_priv = supplied_hex == pub_hex
    else:
        matches_priv = True
    ok_pub = verify_message_pubkey(supplied, sig, msg)

    print(f"=== Signature test ===")
    print(f"signature (base64)       : {base64.b64encode(sig).decode()}")
    print(f"supplied pubkey PEM      : {args.pubkey_pem}")
    print(f"supplied pubkey (compr.) : {supplied_hex}")
    print(f"matches private key      : {matches_priv}")
    print(f"signature verifies vs it : {ok_pub}")
    print()

    if pub_hex:
        if supplied_hex != pub_hex:
            print("!!! supplied public key does not match wallet pub key")
    if not ok_pub:
        sys.exit("!!! supplied privkey does not generate a valid signature")
    print("Wallet checks complete")

if __name__ == "__main__":
    main()
