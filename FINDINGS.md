# RT-950 Pro — findings

What is actually known about this radio, how it was established, and which
earlier conclusions turned out to be wrong.

Confidence words are used literally throughout. **Confirmed** means checked
against the hardware or against bytes the radio itself wrote. **Derived** means
read out of disassembly. **Inferred** means it fits the evidence and has not
been tested. Anything not marked is not established.

---

## 1. Hardware

| | |
|---|---|
| MCU | Artery AT32F403A, ARM Cortex-M4F |
| Transceivers | two — BK4819 and BK4829, driven through an ops table |
| Broadcast RX | SI4732 (FM/AM/SSB) |
| Display | ST7789V, 240x320 |
| Config storage | external SPI flash, 64 KiB read back |
| Firmware seen | V0.27 (as shipped), V0.29 (current) |

The RT-890, whose open firmware served as the reference, is a **different SoC**
but shares the BK4819/BK4829 family. Register-level constants often transfer.
Absolute addresses never do.

---

## 2. Firmware image layout — confirmed

The `.BTF` update file is not a flat image. Three regions:

```
file 0x000-0x3FF   ->  addr file + 0x08003000    plaintext stub: vector table + reset
file 0x400-0x7FF   ->  NEVER PROGRAMMED          16-byte base key + padding
file 0x800-end     ->  addr file + 0x08002C00    application body, encrypted
```

Load base is **0x08003000**, confirmed by the reset vector `0x080032A1` and the
initial SP `0x20017BB0`. `tools/build_flat_image.py` produces an image where
address == 0x08003000 + file offset.

The firmware sets `SCB->VTOR` (0xE000ED08) itself via
`nvic_vector_table_set(base, offset & 0x1FFFFF80)`.

### 2.1 Two wrong answers about the base — recorded deliberately

The inherited Ghidra project used base **0x80000000**. That is wrong, and it is
worth stating *how* it was visibly wrong: 1,955 `DAT_` symbols landed in the
code region against 23 in SRAM. That ratio is backwards for any firmware, and it
is the kind of signal that should have prompted a re-import immediately.

Then two of my own wrong answers, in order:

1. **0x08000000.** Close, and wrong.
2. **"There is a 0x2C00 hole in the file."** There is no hole. I invented a gap
   to explain an offset rather than question the base I had already committed
   to, and built `build_corrected_image.py` on that false premise. Retracted.

The real answer was in a docstring in `fwcrypt_io.py` — key at 0x400,
decryption from 0x800, first two 1 KiB blocks untouched. **Read the prose before
doing the archaeology.** This happened twice; the other time the answer was in
Hertzz58's README, describing the bootloader.

---

## 3. Channel records — confirmed byte-for-byte

32 bytes per record, 999 records from 0x0000.

```
0x00  4  rx frequency    little-endian packed BCD, 10 Hz units
0x04  4  tx frequency    same, or FF FF FF FF = receive-only
0x08  2  rx tone         little-endian, 0 = carrier squelch
0x0A  2  tx tone         little-endian, 0 = none
0x0C  3  always 00       unmodelled
0x0F  1  flags           bit6 wide, bits5-4 mute, bit3 lockout,
                         bit2 scan add, bit0 code break
0x10  4  always FF       unmodelled
0x14 12  name            ASCII, 0xFF-padded
```

Frequency: 462.5625 MHz stores as `50 62 25 46`. Confirmed against records the
radio wrote.

Tones: CTCSS is frequency x 10 (`55 05` = 0x0555 = 1365 = 136.5 Hz). DCS is a
**1-based index** into the standard 104-code table, so a stored 15 means DCS
073 — not DCS 015. A channel was once flagged as suspect on the assumption it
held the code directly; the channel was fine and the reading was wrong.

**The flag byte is at 0x0F, not 0x0C.** An earlier version of this document put
flags at 0x0C and transmit power at 0x0D, derived from the *field order* in the
RT-900 vendor struct without checking offsets against data. No field for
transmit power has been located anywhere in the record. Bytes 0x0C-0x0E and
0x10-0x13 are constant across all 91 programmed records, so nothing can be
concluded about them; the tooling copies them through rather than guessing.

Verification: `build_channels.py --selftest` re-encodes every programmed record
and requires byte-identical output. 91/91 pass.

---

## 4. Zone names — 0xC000, and a correction

```
0xC000  "ZoneOne"     0xC050  "ZoneSix"
0xC010  "ZoneTwo"     0xC060  "ZoneSeven"
0xC020  "ZoneThree"   0xC070  "ZoneEight"
0xC030  "ZoneFour"    0xC080  "ZoneNine"
0xC040  "ZoneFive"    0xC090  "ZoneTen"
0xC0A0  erased
```

Ten slots, 16-byte pitch, 12 bytes of text, 0xFF-padded.

**This was previously recorded as 0xA200. That was wrong**, and it was shipped
as a firmware "fix" (PR #2) that would have broken zone names on every radio.
Two errors compounded:

1. A dump region had been hand-labelled `dtmf_modulation_0xC000`. That label was
   a *guess*. It was later cited as established fact to rule out 0xC000 — a
   guess laundered into evidence, then used to reject the correct answer.
2. Radtel's RT-900 source does declare `BANK_NAME_ADDR 0xA200`. But the RT-900
   is a BT32F0x Cortex-M0 — a different radio. On the RT-950, 0xA200 is erased.

The 0xA200 commit claimed verification "two independent ways against a physical
radio." Neither survives contact with a dump. Both claims are withdrawn.

**Rule adopted:** the RT-900 source is authoritative for record *structure*
(CHAN_SIZE 32, name at offset 20, 12 bytes — all confirmed) and for nothing
about absolute addresses. Check addresses against a dump.

---

## 5. Behaviour — confirmed on hardware

- **The radio caches its channel list at boot.** Always power-cycle after a
  write. A stale display looks exactly like a failed write and cost real time.
- **Gaps between programmed channels are skipped by the knob.** A test channel
  at slot 100 made the display jump 90 -> 101. Spacing groups out is therefore
  free, and the plan uses it.
- **Channel numbering shown on screen is 1-based.** Tooling matches that, since
  mismatched bases make every comparison with the radio ambiguous.

## 6. Tuning steps

The offered steps are 2.5 / 5 / 6.25 / 10 / 12.5 / 25 kHz.

For 2 m repeaters on the US 15 kHz plan, **5 kHz is the only offered step that
lands on every channel** — 15 is a multiple of 5. 12.5 kHz never lands on them
at all. An earlier recommendation of 12.5 kHz as "closest to 15" was wrong;
closeness of the step size is irrelevant, divisibility is what matters.

---

## 7. Zone-enable state

The OEM keeps a 15-bit zone-enable field at SRAM `0x2000A394`, but it is
**derived at boot, not persisted**. The planned zones-as-filter feature
therefore needs its own storage; it cannot reuse this.

---

## 8. Standing lessons

1. **Read the prose first.** Two multi-hour detours would have been avoided by
   reading a docstring and a README that were already on disk.
2. **Verify by counting the thing you care about, not by exit status.** A naming
   script applied zero names and exited 0, twice.
3. **Never let a label become evidence.** The zone-address error traces entirely
   to a hand-written filename being treated as fact.
4. **A reference implementation for a different SoC transfers structure, not
   addresses.**
5. **Round-trip tests catch what re-reading notes does not.** Both layout
   corrections in this document came from the selftest failing, not from review.
