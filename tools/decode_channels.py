#!/usr/bin/env python3
"""Decode RT-950 Pro channel memory into a readable table.

    python3 tools/decode_channels.py DUMP.bin [--csv out.csv] [--zones]

DUMP.bin is a raw read of the radio's config flash (offset 0 == CHAN_ADDR).

Record layout, 32 bytes, from the RT-900 vendor STR_CHANNEL and confirmed
against a CPS-programmed radio:

    0x00  4  rx frequency   little-endian packed BCD, 10 Hz units
    0x04  4  tx frequency   same
    0x08  2  rx tone        CTCSS freq*10, or 1-based DCS index, 0 = none
    0x0A  2  tx tone        same
    0x0C  1  flags          bit6 bandwidth (1=wide), bits5-4 mute mode,
                            bit3 busy lockout, bit2 scan add, bit0 code break
    0x0D  1  power          0 low / 1 mid / 2 high
    0x0E  6  reserved / per-model extras
    0x14 12  name           ASCII, 0xFF-terminated
"""

import argparse
import csv
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rt950_codec import (CHAN_ADDR, CHAN_SIZE, CHAN_MAX, NAME_OFFSET, NAME_SIZE,
                         ZONE_NAME_ADDR, ZONE_NAME_STRIDE, ZONE_NAME_SIZE, ZONE_MAX,
                         dec_freq, dec_tone, dec_name)


def is_blank(rec: bytes) -> bool:
    return rec == b"\xFF" * len(rec) or rec == b"\x00" * len(rec)


def decode_record(rec: bytes) -> dict:
    rx = dec_freq(rec[0:4])
    tx = dec_freq(rec[4:8])
    rxt, txt = struct.unpack("<HH", rec[8:12])
    flags, power = rec[12], rec[13]
    return {
        "rx_mhz":   f"{rx / 1e6:.4f}",
        "tx_mhz":   f"{tx / 1e6:.4f}",
        "offset":   f"{(tx - rx) / 1e6:+.4f}" if tx != rx else "",
        "rx_tone":  dec_tone(rxt),
        "tx_tone":  dec_tone(txt),
        "bw":       "wide" if flags & 0x40 else "narrow",
        "mute":     (flags >> 4) & 0x03,
        "lockout":  bool(flags & 0x08),
        "scan":     bool(flags & 0x04),
        "power":    {0: "low", 1: "mid", 2: "high"}.get(power, str(power)),
        "flags":    f"0x{flags:02X}",
        "name":     dec_name(rec[NAME_OFFSET:NAME_OFFSET + NAME_SIZE]),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dump", type=Path)
    ap.add_argument("--csv", type=Path, help="write a CSV instead of a table")
    ap.add_argument("--zones", action="store_true", help="also list zone names")
    ap.add_argument("--base", type=lambda s: int(s, 0), default=0,
                    help="offset in the file where CHAN_ADDR lives (default 0)")
    args = ap.parse_args()

    data = args.dump.read_bytes()
    print(f"[*] {args.dump}  {len(data)} bytes", file=sys.stderr)

    rows = []
    for ch in range(CHAN_MAX + 1):
        off = args.base + CHAN_ADDR + ch * CHAN_SIZE
        if off + CHAN_SIZE > len(data):
            break
        rec = data[off:off + CHAN_SIZE]
        if is_blank(rec):
            continue
        try:
            d = decode_record(rec)
        except Exception as e:                      # a malformed record is data, not a crash
            rows.append({"ch": ch + 1, "name": f"<undecodable: {e}>"})
            continue
        # Display numbering is 1-based -- that is what the radio's screen shows,
        # and matching it avoids off-by-one confusion when comparing to the radio.
        d["ch"] = ch + 1
        rows.append(d)

    print(f"[+] {len(rows)} programmed channels", file=sys.stderr)

    cols = ["ch", "name", "rx_mhz", "tx_mhz", "offset", "rx_tone", "tx_tone",
            "bw", "power", "scan", "lockout", "mute", "flags"]

    if args.csv:
        with args.csv.open("w", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            w.writerows(rows)
        print(f"[+] wrote {args.csv}", file=sys.stderr)
    else:
        print(f"{'CH':>4}  {'NAME':<12} {'RX':>10} {'TX':>10} {'OFFSET':>9} "
              f"{'RXTONE':>7} {'TXTONE':>7}  {'BW':<6} {'PWR':<4} SCAN")
        print("-" * 92)
        for r in rows:
            if "rx_mhz" not in r:
                print(f"{r['ch']:>4}  {r['name']}")
                continue
            print(f"{r['ch']:>4}  {r['name']:<12} {r['rx_mhz']:>10} {r['tx_mhz']:>10} "
                  f"{r['offset']:>9} {r['rx_tone']:>7} {r['tx_tone']:>7}  "
                  f"{r['bw']:<6} {r['power']:<4} {'y' if r['scan'] else ''}")

    if args.zones:
        print("\nZONES", file=sys.stderr)
        for z in range(ZONE_MAX + 1):
            off = args.base + ZONE_NAME_ADDR + z * ZONE_NAME_STRIDE
            if off + ZONE_NAME_SIZE > len(data):
                break
            name = dec_name(data[off:off + ZONE_NAME_SIZE])
            if name:
                print(f"  zone {z:2d}  {name}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
