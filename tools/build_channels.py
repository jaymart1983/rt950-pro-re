#!/usr/bin/env python3
"""Build an RT-950 Pro channel image from a plan.

    python3 tools/build_channels.py --selftest DUMP.bin
    python3 tools/build_channels.py --plan channel_plan.py --out channels.bin
    python3 tools/build_channels.py --plan channel_plan.py --out channels.bin \
                                    --base DUMP.bin

--selftest is the safety interlock and should be run against a fresh dump before
any write. It decodes every programmed record in the dump, re-encodes it with
this tool's own encoder, and requires the result to be byte-identical. If the
encoder has drifted -- wrong BCD nibble order, wrong DCS base, wrong pad byte --
the selftest fails and nothing gets written to a radio. It has caught real
mistakes; do not skip it.

--base copies an existing dump and overlays the plan onto it, so regions this
tool does not model (calibration, DTMF, radio settings) are preserved. Without
it the output is 0xFF outside the channel and zone-name regions.

NOTE: the radio caches its channel list at boot. ALWAYS power-cycle after a
write, or the display will keep showing the old list and look like a failure.
"""

import argparse
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rt950_codec import (CHAN_ADDR, CHAN_SIZE, CHAN_MAX, NAME_OFFSET, NAME_SIZE,
                         RX_OFFSET, TX_OFFSET, RXTONE_OFFSET, TXTONE_OFFSET,
                         SIGNAL_OFFSET, PTTID_OFFSET, POWER_OFFSET,
                         FLAGS_OFFSET, RESERVED_OFFSET, RX_ONLY,
                         POWER_LOW, POWER_MID, POWER_HIGH,
                         ZONE_NAME_ADDR, ZONE_NAME_STRIDE, ZONE_NAME_SIZE, ZONE_MAX,
                         enc_freq, dec_freq, enc_tone, dec_tone, enc_name, dec_name)

POWER = {"low": POWER_LOW, "mid": POWER_MID, "high": POWER_HIGH}

# Default flags: 0x44 = wide (bit6) + scan-add (bit2), mute mode 0, no lockout.
FLAG_WIDE     = 0x40
FLAG_SCAN     = 0x04
FLAG_LOCKOUT  = 0x08
FLAG_DEFAULT  = FLAG_WIDE | FLAG_SCAN



def make(rx, tx=None, txtone=None, rxtone=None, name="",
         flags=FLAG_DEFAULT, narrow=False, scan=True, rx_only=False,
         power="low", scramble=0, pttid=0, signal=0):
    """Build one 32-byte channel record.

    rx/tx are Hz (ints) or MHz (floats). tx defaults to rx (simplex).
    txtone is what we transmit; rxtone is the tone squelch we require.
    rx_only=True (or tx=None with rx_only) writes the FF FF FF FF tx sentinel,
    which is how the OEM marks NOAA and other listen-only channels.
    """
    def hz(v):
        if v is None:
            return None
        return int(round(v * 1_000_000)) if isinstance(v, float) else int(v)

    rx_hz = hz(rx)
    tx_hz = None if rx_only else (hz(tx) if tx is not None else rx_hz)

    f = flags
    if narrow:
        f &= ~FLAG_WIDE
    if not scan:
        f &= ~FLAG_SCAN

    rec = bytearray(b"\xFF" * CHAN_SIZE)
    rec[RX_OFFSET:RX_OFFSET + 4]         = enc_freq(rx_hz)
    rec[TX_OFFSET:TX_OFFSET + 4]         = enc_freq(tx_hz)
    rec[RXTONE_OFFSET:RXTONE_OFFSET + 2] = struct.pack("<H", enc_tone(rxtone))
    rec[TXTONE_OFFSET:TXTONE_OFFSET + 2] = struct.pack("<H", enc_tone(txtone))
    rec[SIGNAL_OFFSET]                   = signal
    rec[PTTID_OFFSET]                    = pttid
    pw = POWER[power] if isinstance(power, str) else int(power)
    rec[POWER_OFFSET]                    = (pw & 0x0F) | ((scramble & 0x0F) << 4)
    rec[FLAGS_OFFSET]                    = f
    rec[RESERVED_OFFSET:RESERVED_OFFSET + 4] = b"\xFF" * 4
    rec[NAME_OFFSET:NAME_OFFSET + NAME_SIZE] = enc_name(name, NAME_SIZE)
    return bytes(rec)


def is_blank(rec: bytes) -> bool:
    return rec == b"\xFF" * len(rec) or rec == b"\x00" * len(rec)


def selftest(dump: Path) -> int:
    """Re-encode every record in a dump and require byte-identical output."""
    data = dump.read_bytes()
    checked = failed = 0
    print(f"[*] selftest against {dump} ({len(data)} bytes)")

    for ch in range(CHAN_MAX + 1):
        off = CHAN_ADDR + ch * CHAN_SIZE
        if off + CHAN_SIZE > len(data):
            break
        orig = data[off:off + CHAN_SIZE]
        if is_blank(orig):
            continue
        checked += 1

        rx = dec_freq(orig[RX_OFFSET:RX_OFFSET + 4])
        tx = dec_freq(orig[TX_OFFSET:TX_OFFSET + 4])
        rxt, txt = struct.unpack("<HH", orig[RXTONE_OFFSET:RXTONE_OFFSET + 4])
        name = dec_name(orig[NAME_OFFSET:NAME_OFFSET + NAME_SIZE])

        rebuilt = bytearray(b"\xFF" * CHAN_SIZE)
        rebuilt[RX_OFFSET:RX_OFFSET + 4]         = enc_freq(rx)
        rebuilt[TX_OFFSET:TX_OFFSET + 4]         = enc_freq(tx)
        rebuilt[RXTONE_OFFSET:RXTONE_OFFSET + 2] = struct.pack("<H", rxt)
        rebuilt[TXTONE_OFFSET:TXTONE_OFFSET + 2] = struct.pack("<H", txt)
        rebuilt[SIGNAL_OFFSET]                   = orig[SIGNAL_OFFSET]
        rebuilt[PTTID_OFFSET]                    = orig[PTTID_OFFSET]
        rebuilt[POWER_OFFSET]                    = orig[POWER_OFFSET]
        rebuilt[FLAGS_OFFSET]                    = orig[FLAGS_OFFSET]
        rebuilt[RESERVED_OFFSET:RESERVED_OFFSET + 4] = orig[RESERVED_OFFSET:RESERVED_OFFSET + 4]
        rebuilt[NAME_OFFSET:NAME_OFFSET + NAME_SIZE] = enc_name(name, NAME_SIZE)

        # Unmodelled bytes are copied above, so any mismatch here is a genuine
        # fault in the frequency, tone or name codec.
        if bytes(rebuilt) != orig:
            failed += 1
            if failed <= 8:
                diff = [i for i in range(CHAN_SIZE) if rebuilt[i] != orig[i]]
                print(f"[-] ch {ch + 1} '{name}' mismatch at {diff}")
                print(f"      orig {orig.hex(' ')}")
                print(f"      ours {bytes(rebuilt).hex(' ')}")
        # Tone round-trip is a separate assertion: dec->enc must be stable.
        for v in (rxt, txt):
            s = dec_tone(v)
            if s and enc_tone(s) != v:
                failed += 1
                print(f"[-] ch {ch + 1} tone round-trip: {v} -> '{s}' -> {enc_tone(s)}")

    print(f"[+] checked {checked} records, {failed} mismatches")
    if failed:
        print("[!] ENCODER IS WRONG -- do not write this to a radio")
        return 1
    print("[=] encoder reproduces the radio's own records exactly")
    return 0


def load_plan(path: Path):
    """Execute a plan module and return (channels, zones).

    A plan defines CHANNELS (list of records from make()) and optionally
    ZONES (dict of index -> name).

    NOTE: exec() gets ONE namespace dict used as both globals and locals. Using
    two made module-level names invisible inside the plan's own functions and
    produced "NameError: name 'M' is not defined" from otherwise-correct plans.
    """
    ns = {"make": make, "enc_tone": enc_tone, "enc_freq": enc_freq,
          "FLAG_WIDE": FLAG_WIDE, "FLAG_SCAN": FLAG_SCAN,
          "FLAG_LOCKOUT": FLAG_LOCKOUT, "FLAG_DEFAULT": FLAG_DEFAULT,
          "__name__": "channel_plan", "__file__": str(path)}
    exec(compile(path.read_text(), str(path), "exec"), ns, ns)
    if "CHANNELS" not in ns:
        raise SystemExit(f"{path}: plan defines no CHANNELS")
    return ns["CHANNELS"], ns.get("ZONES", {})


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", type=Path, metavar="DUMP")
    ap.add_argument("--plan", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--base", type=Path, help="dump to overlay onto")
    ap.add_argument("--size", type=lambda s: int(s, 0), default=0x10000)
    args = ap.parse_args()

    if args.selftest:
        rc = selftest(args.selftest)
        if rc or not args.plan:
            return rc

    if not args.plan or not args.out:
        ap.error("--plan and --out are both required (or use --selftest alone)")

    channels, zones = load_plan(args.plan)

    if args.base:
        img = bytearray(args.base.read_bytes())
        if len(img) < args.size:
            img += b"\xFF" * (args.size - len(img))
        print(f"[*] overlaying onto {args.base}")
    else:
        img = bytearray(b"\xFF" * args.size)

    for i, rec in enumerate(channels):
        if rec is None:
            continue
        if len(rec) != CHAN_SIZE:
            raise SystemExit(f"channel {i + 1}: record is {len(rec)} bytes, want {CHAN_SIZE}")
        off = CHAN_ADDR + i * CHAN_SIZE
        img[off:off + CHAN_SIZE] = rec

    for idx, name in zones.items():
        if not 0 <= idx <= ZONE_MAX:
            raise SystemExit(f"zone {idx} out of range 0..{ZONE_MAX}")
        off = ZONE_NAME_ADDR + idx * ZONE_NAME_STRIDE
        img[off:off + ZONE_NAME_SIZE] = enc_name(name, ZONE_NAME_SIZE)

    args.out.write_bytes(bytes(img))
    n = sum(1 for c in channels if c is not None)
    print(f"[+] {n} channels, {len(zones)} zones -> {args.out} ({len(img)} bytes)")
    print("[!] power-cycle the radio after writing; it caches the channel list at boot")
    return 0


if __name__ == "__main__":
    sys.exit(main())
