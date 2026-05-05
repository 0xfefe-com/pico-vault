#!/usr/bin/env python3
"""
Parallel offline brute-forcer for the pico_vault challenge.

Dependencies:
    pip install cryptography
"""

from __future__ import annotations

import argparse
import multiprocessing as mp
import sys
import threading
import time
from typing import Any

import cryptography
import hashlib

KEY_LEN = # Finish this
IV_LEN  = # Finish this
CT_LEN  = # Finish this
TAG_LEN = # Finish this

def verify_single(
    pin: bytes,
    salt: bytes,
    iv: bytes,
    ct: bytes,
    tag: bytes,
    iters: int,
) -> bytes | None:
    # Finish this

# Per worker global
_W: dict[str, Any] = {}

def _worker_init(
    salt: bytes,
    iv: bytes,
    ct: bytes,
    tag: bytes,
    iters: int,
    pin_len: int,
    found_flag: Any,
    processed: Any,
) -> None:
    _W["salt"]      = salt
    _W["iv"]        = iv
    _W["ct"]        = ct
    _W["tag"]       = tag
    _W["iters"]     = iters
    _W["pin_len"]   = pin_len
    _W["found"]     = found_flag
    _W["processed"] = processed

def _try_range(args: tuple[int, int]) -> tuple[str, str, int] | None:
    start, end = args
    salt      = _W["salt"]
    iv        = _W["iv"]
    ct        = _W["ct"]
    tag       = _W["tag"]
    iters     = _W["iters"]
    pin_len   = _W["pin_len"]
    found     = _W["found"]
    processed = _W["processed"]

    fmt = "{{:0{}d}}".format(pin_len)
    progress_step = 4096
    local_done = 0

    for i in range(start, end):
        if (i & (progress_step - 1)) == 0:
            with processed.get_lock():
                processed.value += local_done
            local_done = 0
            if found.value:
                return None
        pin = fmt.format(i).encode()
        local_done += 1
        pt = verify_single(pin, salt, iv, ct, tag, iters)
        if pt is None:
            continue
        with processed.get_lock():
            processed.value += local_done
        with found.get_lock():
            if not found.value:
                found.value = 1
                return (pin.decode(), pt.hex(), i)
        return None

    with processed.get_lock():
        processed.value += local_done
    return None

def parse_hex(s: str, expected_len: int | None = None, name: str = "") -> bytes:
    raw = bytes.fromhex(s)
    if expected_len is not None and len(raw) != expected_len:
        sys.exit(f"bad --{name}: expected {expected_len} bytes, got {len(raw)}")
    return raw

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Parallel offline brute-forcer for the pico_vault "
                    "challenge (Python port of pico_vault_bf.c).",
        formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--salt-hex", required=True)
    ap.add_argument("--iv-hex",   required=True)
    ap.add_argument("--ct-hex",   required=True)
    ap.add_argument("--tag-hex",  required=True)
    ap.add_argument("--iters",    required=True, type=int)
    ap.add_argument("--pin-len",  type=int)
    ap.add_argument("--threads",  type=int, default=1,
                    help="worker processes (default: 1)")
    ap.add_argument("--pin",      default=None,
                    help="verify a single PIN, skip the PIN search loop")
    args = ap.parse_args()

    salt = parse_hex(args.salt_hex,             name="salt-hex")
    iv   = parse_hex(args.iv_hex,  IV_LEN,      name="iv-hex")
    ct   = parse_hex(args.ct_hex,  CT_LEN,      name="ct-hex")
    tag  = parse_hex(args.tag_hex, TAG_LEN,     name="tag-hex")

    iters   = args.iters

    # Single PIN check
    if args.pin is not None:
        if not args.pin.isdigit():
            sys.exit("--pin must be ASCII digits only")
        print(f"[verify] pin=\"{args.pin}\" salt-len={len(salt)}")
        pt = verify_single(args.pin.encode(), salt, iv, ct, tag, iters)
        if pt is None:
            raise SystemExit("[verify] PIN wrong")
        return 0

    # Bruteforce loop
    if not (1 <= args.pin_len <= 12):
        sys.exit("bad pin-len")

    threads = max(1, args.threads)

    total = 10 ** args.pin_len   
    chunk = (total + threads - 1) // threads
    ranges = [(i * chunk, min(total, (i + 1) * chunk)) for i in range(threads)]
    print(f"[brute] threads={threads} total={total}")  

    found_flag = mp.Value("i", 0)
    processed  = mp.Value("Q", 0)
    start_t    = time.time()

    stop_progress = threading.Event()

    def _progress() -> None:
        while not stop_progress.is_set():
            time.sleep(1.0)
            cur = processed.value
            el  = time.time() - start_t
            if cur == 0 or el == 0:
                continue
            rate = cur / el
            pct  = 100.0 * cur / total
            eta  = (total - cur) / rate if rate > 0 else 0.0
            sys.stderr.write(
                f"\r[brute] {pct:6.2f}% ({cur}/{total}) "
                f"{rate:.0f} PIN/s ETA {eta:.0f}s   ")
            sys.stderr.flush()
        sys.stderr.write("\n")
        sys.stderr.flush()

    prog_thr = threading.Thread(target=_progress, daemon=True)
    prog_thr.start()

    pool = mp.Pool(threads, initializer=_worker_init,
                   initargs=(salt, iv, ct, tag, iters, args.pin_len,
                             found_flag, processed))

    result = None
    try:
        for r in pool.imap_unordered(_try_range, ranges):
            if r is not None:
                result = r
                with found_flag.get_lock():
                    found_flag.value = 1
                break
    finally:
        pool.terminate()
        pool.join()
        stop_progress.set()
        prog_thr.join()

    elapsed = time.time() - start_t
    if result is None:
        print(f"\n[brute] PIN not found in search space ({elapsed:.1f}s)",
              file=sys.stderr)
        return 1

    pin, pt_hex, idx = result
    rate = (idx + 1) / elapsed if elapsed > 0 else 0.0
    print(f"\n[brute] FOUND PIN: {pin}  ({elapsed:.1f}s, ~{rate:.0f} PIN/s)")
    print(f"[brute] plaintext: {pt_hex}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
