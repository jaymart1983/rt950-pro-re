"""Encoding primitives for RT-950 Pro channel memory.

Shared by build_channels.py and decode_channels.py so that the encoder and the
decoder cannot drift apart -- which matters, because the only real check we have
is that decode(encode(x)) round-trips against records the radio itself wrote.

Everything here was confirmed against a dump of a radio programmed by the OEM
CPS, and cross-checked against the RT-900 vendor headers (Driver/AddrMap.h and
Common/PublType.h), which describe the same family.
"""

# ---------------------------------------------------------------- flash layout

CHAN_ADDR       = 0x0000   # channel records
CHAN_SIZE       = 32       # bytes per record
CHAN_MAX        = 999
BANK_SIZE       = 2048
BANK_CH_NUM     = 64

# Record layout, verified byte-for-byte against a dump of this radio.
#
#   0x00  4  rx frequency    little-endian packed BCD, 10 Hz units
#   0x04  4  tx frequency    same, or FF FF FF FF for a receive-only channel
#   0x08  2  rx tone         little-endian; 0 = carrier squelch
#   0x0A  2  tx tone         little-endian; 0 = no tone
#   0x0C  1  signal code     DTMF group 0-14
#   0x0D  1  PTT-ID          0 off, 1 BOT, 2 EOT, 3 both
#   0x0E  1  power[3:0] / scramble[7:4]
#   0x0F  1  flags           bit6 wide, bit3 busy lockout, bit2 scan add,
#                            bit1 tx enable, bit0 rx modulation
#   0x10  4  reserved        FF in every record observed
#   0x14 12  name            ASCII, 0xFF-padded
#
# The flag byte is at 0x0F, NOT 0x0C. An earlier reconstruction put flags at
# 0x0C and power at 0x0D purely from the vendor struct's field ORDER, without
# checking offsets against real data; the selftest caught it.
#
# The 0x0C-0x0E meanings come from Hertzz58's channel.h, which documents them
# from the OEM V0.27 binary, and are consistent with this dump: every programmed
# record has 00 00 00 there -- signal code 0, PTT-ID off, power 0, scramble off.
# Because all 91 records share one value, the dump CONFIRMS nothing about these
# fields on its own; it only fails to contradict them. Treat as derived, not
# confirmed, until a radio programmed with mixed power levels is dumped.
RX_OFFSET     = 0x00
TX_OFFSET     = 0x04
RXTONE_OFFSET = 0x08
TXTONE_OFFSET = 0x0A
SIGNAL_OFFSET = 0x0C
PTTID_OFFSET  = 0x0D
POWER_OFFSET  = 0x0E    # low nibble power, high nibble scramble
FLAGS_OFFSET  = 0x0F
RESERVED_OFFSET = 0x10
NAME_OFFSET   = 0x14
NAME_SIZE     = 12

# Power encoding is INVERTED from the obvious guess: 0 is HIGH, not low.
# flash_layout.h in the firmware repo documents "Power[3:0] 0=High, 1=Mid,
# 2=Low" from the OEM V0.27 binary. Every record in the dump holds 0, so the
# radio's channels are all at HIGH power -- an earlier version of this file
# assumed 0=low and would have silently written the wrong level.
POWER_HIGH, POWER_MID, POWER_LOW = 0, 1, 2

RX_ONLY = b"\xFF\xFF\xFF\xFF"   # tx field of a receive-only channel (NOAA etc)

VFO_INFO_ADDR   = 0x8000
RADIO_INFO_ADDR = 0x9000
DTMF_INFO_ADDR  = 0xA000

# Zone (bank) names, at 0xC000. A dump of this radio has the ten OEM defaults
# "ZoneOne".."ZoneTen" there at a 16-byte pitch, with 0xC0A0 onward erased.
#
# CORRECTION: this was previously recorded as 0xA200 and that was wrong. The
# region at 0xC000 had been hand-labelled "DTMF/modulation" -- a guess that got
# treated as fact, which then "ruled out" the correct address. Radtel's RT-900
# source does say BANK_NAME_ADDR 0xA200, but the RT-900 is a different radio and
# does not share this layout; on the RT-950 that address is erased.
#
# The RT-900 headers ARE reliable for record structure (CHAN_SIZE 32, name at
# offset 20, 12 bytes) -- every one of those matches. They are not reliable for
# absolute addresses. Verify addresses against a dump, not against the RT-900.
ZONE_NAME_ADDR   = 0xC000
ZONE_NAME_STRIDE = 16      # slot pitch
ZONE_NAME_SIZE   = 12      # bytes of each slot used for text
ZONE_MAX         = 9       # zones 0..9; 0xC0A0 onward is erased

# ------------------------------------------------------------------ CTCSS/DCS

# The standard 104-code DCS list. Channel records store a 1-BASED INDEX into
# this table, not the code itself: stored 15 means DCS 073, not DCS 015. A
# channel was once flagged as suspect on the assumption it held the code
# directly; it was correct and the reading was wrong.
DCS_CODES = [
     23,  25,  26,  31,  32,  36,  43,  47,  51,  53,  54,  65,  71,  72,
     73,  74, 114, 115, 116, 122, 125, 131, 132, 134, 143, 145, 152, 155,
    156, 162, 165, 172, 174, 205, 212, 223, 225, 226, 243, 244, 245, 246,
    251, 252, 255, 261, 263, 265, 266, 271, 274, 306, 311, 315, 325, 331,
    332, 343, 346, 351, 356, 364, 365, 371, 411, 412, 413, 423, 431, 432,
    445, 446, 452, 454, 455, 462, 464, 465, 466, 503, 506, 516, 523, 526,
    532, 546, 565, 606, 612, 624, 627, 631, 632, 654, 662, 664, 703, 712,
    723, 731, 732, 734, 743, 754,
]

CTCSS_TONES = [
     67.0,  69.3,  71.9,  74.4,  77.0,  79.7,  82.5,  85.4,  88.5,  91.5,
     94.8,  97.4, 100.0, 103.5, 107.2, 110.9, 114.8, 118.8, 123.0, 127.3,
    131.8, 136.5, 141.3, 146.2, 151.4, 156.7, 159.8, 162.2, 165.5, 167.9,
    171.3, 173.8, 177.3, 179.9, 183.5, 186.2, 189.9, 192.8, 196.6, 199.5,
    203.5, 206.5, 210.7, 218.1, 225.7, 229.1, 233.6, 241.8, 250.3, 254.1,
]


def enc_freq(hz) -> bytes:
    """Frequency -> 4 bytes, little-endian packed BCD, in units of 10 Hz.

    462.5625 MHz (GMRS 1) -> 46 25 62 50 as BCD digits -> 50 62 25 46 stored.
    Confirmed byte-for-byte against records the radio wrote itself.

    None encodes the receive-only sentinel FF FF FF FF.
    """
    if hz is None:
        return RX_ONLY
    if hz % 10:
        raise ValueError(f"{hz} Hz is not a multiple of 10 Hz")
    units = hz // 10                      # 46256250
    s = f"{units:08d}"
    if len(s) > 8:
        raise ValueError(f"{hz} Hz out of range")
    out = bytearray(4)
    for i in range(4):                    # little-endian pairs
        pair = s[6 - 2 * i: 8 - 2 * i]
        out[i] = (int(pair[0]) << 4) | int(pair[1])
    return bytes(out)


def dec_freq(b: bytes):
    """Inverse of enc_freq. Returns Hz, or None for a receive-only channel."""
    if b == RX_ONLY:
        return None
    digits = ""
    for i in range(3, -1, -1):
        digits += f"{(b[i] >> 4) & 0xF}{b[i] & 0xF}"
    return int(digits) * 10


def enc_tone(t) -> int:
    """Tone spec -> the 16-bit value stored in a channel record.

    None / "" / "off"  -> 0
    "141.3" or 141.3   -> 1413        (CTCSS, frequency x 10)
    "D073" / "D073N"   -> 15          (DCS, 1-based index into DCS_CODES)
    "D073I"            -> 15 | 0x8000 (DCS inverted)
    """
    if t is None:
        return 0
    if isinstance(t, (int, float)):
        return int(round(float(t) * 10))
    s = str(t).strip().upper()
    if not s or s in ("OFF", "NONE", "-"):
        return 0
    if s.startswith("D"):
        body = s[1:]
        inv = False
        if body.endswith("I"):
            inv, body = True, body[:-1]
        elif body.endswith("N"):
            body = body[:-1]
        code = int(body)
        if code not in DCS_CODES:
            raise ValueError(f"DCS {code:03d} is not a standard code")
        v = DCS_CODES.index(code) + 1     # 1-based
        return v | 0x8000 if inv else v
    return int(round(float(s) * 10))


def dec_tone(v: int) -> str:
    """Inverse of enc_tone, as a display string."""
    if v == 0:
        return ""
    inv = bool(v & 0x8000)
    raw = v & 0x7FFF
    if raw <= len(DCS_CODES):             # DCS index range
        return f"D{DCS_CODES[raw - 1]:03d}{'I' if inv else 'N'}"
    return f"{raw / 10:.1f}"


def enc_name(name: str, size: int = NAME_SIZE) -> bytes:
    """Channel/zone name -> fixed-width field, 0xFF-padded.

    0xFF is the pad, not 0x00: erased flash reads as 0xFF and the OEM display
    code stops at the first 0xFF.
    """
    b = name.encode("ascii", "replace")[:size]
    return b + b"\xFF" * (size - len(b))


def dec_name(b: bytes) -> str:
    out = []
    for c in b:
        if c in (0x00, 0xFF):
            break
        out.append(chr(c))
    return "".join(out).rstrip()
