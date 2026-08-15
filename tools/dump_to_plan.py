#!/usr/bin/env python3
"""Regenerate a channel plan from a radio dump.

    python3 tools/dump_to_plan.py DUMP.bin > channel_plan.py

The plan source files were lost with the working tree, but the channels
themselves survived in the radio. This reads them back out and emits a plan that
build_channels.py can rebuild byte-identically -- so the repeater list, tones and
zone layout are recovered from the only copy that still existed.

Verify the round trip before trusting the output:

    python3 tools/dump_to_plan.py DUMP.bin > channel_plan.py
    python3 tools/build_channels.py --plan channel_plan.py --out rebuilt.bin
    cmp <(head -c 31680 DUMP.bin) <(head -c 31680 rebuilt.bin)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from rt950_codec import (CHAN_ADDR, CHAN_SIZE, CHAN_MAX, NAME_OFFSET, NAME_SIZE,
                         RX_OFFSET, TX_OFFSET, RXTONE_OFFSET, TXTONE_OFFSET,
                         FLAGS_OFFSET, ZONE_NAME_ADDR, ZONE_NAME_STRIDE,
                         ZONE_NAME_SIZE, ZONE_MAX,
                         dec_freq, dec_tone, dec_name)
import struct


def q(s):
    return '"' + s.replace('\\', '\\\\').replace('"', '\\"') + '"'


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    data = Path(sys.argv[1]).read_bytes()

    out = []
    out.append('"""Channel plan recovered from a radio dump by tools/dump_to_plan.py.')
    out.append("")
    out.append("Feed to tools/build_channels.py. Channel numbers in comments are the")
    out.append("1-based numbers the radio's display shows.")
    out.append('"""')
    out.append("")
    out.append("CHANNELS = []")
    out.append("")
    out.append("def at(n, rec):")
    out.append("    \"\"\"Place a record at 1-based display channel n, padding gaps with None.")
    out.append("")
    out.append("    Gaps are intentional: the knob skips unprogrammed slots entirely, so")
    out.append("    leaving space between groups costs nothing and keeps each group's")
    out.append("    numbering stable when one is edited.")
    out.append("    \"\"\"")
    out.append("    while len(CHANNELS) < n - 1:")
    out.append("        CHANNELS.append(None)")
    out.append("    if len(CHANNELS) == n - 1:")
    out.append("        CHANNELS.append(rec)")
    out.append("    else:")
    out.append("        CHANNELS[n - 1] = rec")
    out.append("")

    n = 0
    prev = None
    for ch in range(CHAN_MAX + 1):
        off = CHAN_ADDR + ch * CHAN_SIZE
        if off + CHAN_SIZE > len(data):
            break
        rec = data[off:off + CHAN_SIZE]
        if rec == b"\xFF" * CHAN_SIZE or rec == b"\x00" * CHAN_SIZE:
            continue

        rx = dec_freq(rec[RX_OFFSET:RX_OFFSET + 4])
        tx = dec_freq(rec[TX_OFFSET:TX_OFFSET + 4])
        rxt, txt = struct.unpack("<HH", rec[RXTONE_OFFSET:RXTONE_OFFSET + 4])
        flags = rec[FLAGS_OFFSET]
        name = dec_name(rec[NAME_OFFSET:NAME_OFFSET + NAME_SIZE])

        if prev is not None and ch > prev + 1:
            out.append(f"# ---- gap: {ch - prev - 1} unprogrammed slots ----")
        prev = ch

        args = [f"{rx}"]
        if tx is None:
            args.append("rx_only=True")
        elif tx != rx:
            args.append(f"tx={tx}")
        if txt:
            args.append(f"txtone={q(dec_tone(txt))}")
        if rxt:
            args.append(f"rxtone={q(dec_tone(rxt))}")
        args.append(f"name={q(name)}")
        if flags != 0x44:
            args.append(f"flags=0x{flags:02X}")

        rxs = f"{rx / 1e6:.4f}"
        note = f"  # {rxs}"
        if tx is not None and tx != rx:
            note += f" / tx {tx / 1e6:.4f} ({(tx - rx) / 1e6:+.1f})"
        elif tx is None:
            note += " rx-only"
        if txt:
            note += f"  tone {dec_tone(txt)}"

        out.append(f"at({ch + 1}, make({', '.join(args)}))" + note)
        n += 1

    zones = {}
    for z in range(ZONE_MAX + 1):
        off = ZONE_NAME_ADDR + z * ZONE_NAME_STRIDE
        if off + ZONE_NAME_SIZE > len(data):
            break
        nm = dec_name(data[off:off + ZONE_NAME_SIZE])
        if nm:
            zones[z] = nm

    out.append("")
    out.append("ZONES = {")
    for z, nm in sorted(zones.items()):
        out.append(f"    {z}: {q(nm)},")
    out.append("}")
    out.append("")

    print("\n".join(out))
    print(f"[+] {n} channels, {len(zones)} zones recovered", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
