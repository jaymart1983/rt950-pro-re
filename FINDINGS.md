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
0x0C  1  signal code     DTMF group 0-14
0x0D  1  PTT-ID          0 off, 1 BOT, 2 EOT, 3 both
0x0E  1  power[3:0] / scramble[7:4]
0x0F  1  flags           bit6 wide, bit3 busy lockout, bit2 scan add,
                         bit1 tx enable, bit0 rx modulation
0x10  4  reserved        FF in every record observed
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
RT-900 vendor struct without checking offsets against data.

The 0x0C-0x0E meanings come from Hertzz58's `channel.h`, which documents them
from the OEM V0.27 binary and independently agrees that flags sit at 0x0F. Every
programmed record here holds `00 00 00` there, which is consistent with those
meanings but **confirms nothing** — one value across all 91 records cannot
distinguish between field layouts. Marked *derived*, not *confirmed*, until a
radio programmed with mixed power levels is dumped.

I had briefly written that no transmit-power field existed. It does; I had not
read the header in the fork I was already working in.

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

## 8. Hardware bring-up — confirmed on the radio

Everything below was measured on a physical RT-950 Pro, not inferred.

### 8.1 The bootloader drops the last block of every upload

Confirmed by having the firmware checksum its own flash a kilobyte at a time and
comparing against the `.bin`:

```
BLK 0..7   match exactly
BLK 8      53907 expected, 106141 actual    <- last block sent
```

Padding the image to a whole number of blocks was **not** sufficient; with the
image at exactly ten full blocks the last one still failed. `encrypt_btf.py` now
appends a whole sacrificial block of `0xFF`.

This one fault produced three unrelated-looking symptoms, each chased separately
for hours:

* LCD font glyphs rendering as garbage ("looks Chinese")
* `HANDSHAKE[]` reading as random bytes, so the update listener never matched
* almost certainly the garbled main screen that started the whole investigation

Late `.rodata` lives in that tail. Anything at the end of the image is at risk.

### 8.2 The bootloader has no soft entry — the app must program itself

Its `main()` is:

```
gpio_init / lcd_gpio_init / uart_init
check_update_button   -> uart_update_mode
check_spi_model / check_spi_flag
-> otherwise jump to the application
```

Physical buttons or an SPI-flash marker. **No RAM flag, no magic value, no
command.** Hours went into faking the side-button GPIOs, branching to its reset
vector, and calling `uart_update_mode()` directly. None of it could have worked.

Radtel's own firmware never tries. The RT-900 source shows the application
setting `MODE_FLASH_PROGRAM`, programming flash itself, and calling
`NVIC_SystemReset()` when done. The bootloader is a **recovery** path, not an
update path. `src/app/updater.c` now does the same, and zero-touch flashing
works.

The updater must buffer the whole image before writing anything: interleaving
receive with erase loses every byte arriving during a sector erase (the UART
holds one byte and interrupts are off). It failed reproducibly at block 8.

### 8.3 UART: CR2/CR3 were never initialised

UART4 inherited the bootloader's framing configuration, giving consistent
per-byte corruption that looked like a baud error but was not — a sweep from
104k to 136k produced a flat plateau of identical wrong bytes.

```
sent:  74 69 63 6b 20 23    "tick #"
recv:  b6 20 b4 e6 5e 3e
```

### 8.4 The hardware tests printed to the wrong UART

`hw_test.c` defines its own `dbg_puts` writing to **USART1 — the Bluetooth
port** — shadowing the global one that writes UART4. Every test printed
diagnostics nothing could receive, so a working test was indistinguishable from
a dead radio.

### 8.5 Keypad — the pinmap's matrix table is wrong in every position

Measured by driving each column and reading raw rows with a key held:

| driven | keys | table claimed |
|---|---|---|
| PC0 | OK, ABC, Back, V/M | 1 4 7 ★ |
| PC1 | 3, 6, 9, # | 2 5 8 0 |
| PC2 | 2, 5, 8, 0 | 3 6 9 # |
| PC3 | Up, Down, Left, Right | OK ABC Back V/M |
| all HIGH | 1, 4, 7, ★ | the arrows |

Three separate faults, all needed fixing:

1. **Mapping** — `col * 4 + row` assumed the table's order.
2. **Settle time** — `scan_delay()` spun 10 times, under a microsecond. Rows use
   the internal pull-ups (~40k) and need far longer. Symptom: correct ROW every
   time, always attributed to PC0.
3. **Scan order** — the 5th-column keys are driven by nothing and pull their row
   low in every state, so PC0 claimed them. The all-high state is now tested
   first.

Key legends do **not** match the constant names: `KEY_A_VFO` is the ABC key,
`KEY_B_SCAN` is Back, `KEY_C_MENU` is OK, `KEY_D_BAND` is V/M.

### 8.6 The encoder is half-step

One physical click produces **two** quadrature transitions, not four. Emitting a
detent every 4 steps halved every movement. `ENC_STEPS_PER_DETENT` is 2.

### 8.7 Power — deep sleep, not a hardware cut

Releasing the PB9 latch does **not** collapse the rail. Proven: the CPU keeps
executing afterwards, which it could not do if the supply had dropped.

`power_off()` originally ended in `for (;;) __WFI()`, which hung the CPU with
interrupts masked — the radio looked off but was alive and unrecoverable without
a battery pull.

It now enters **STOP mode**, woken by the switch on **EXTI line 0** (PE0). Every
clock halted, microamps, immediate wake. Off and on both work from the knob.

**PA11, labelled "DEVICE POWER OFF" in the pinmap, does nothing on either
polarity.** That label is `HW_PROBED` — inferred, not observed — and is wrong,
exactly like the keypad table. The OEM shutdown address cited in `power.c`
(`0x0801E2A4`) also holds unrelated code. A genuine hardware cut has not been
found; the remaining lead is the full OEM decompile.

### 8.8 Anything registered with sched_register() is invisible to HW_TEST

`HW_TEST` builds do not run the scheduler. `power_button_poll()` and the encoder
task are registered that way, so both looked completely dead in test builds when
the code was fine. This cost time twice.

### 8.9 Other confirmed

* **SPI flash reads correctly** — channel 1 returns `GMRS 1 / 462.5625 MHz`,
  byte-identical to the dump. `spi_flash_read_id()` is buggy though, returning
  `5E 40 16` instead of `EF 40 15`; data reads are unaffected.
* **LCD** — text, 240x320 geometry and native RGB565 all confirmed. Two driver
  bugs fixed: `lcd_set_data` read-modify-wrote the whole GPIOD register (the
  keypad rows are PD4-PD7 on that port), and the WR strobe was ~33 ns with no
  setup time, which could put the address window in the wrong place.

## 9. Standing lessons

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
6. **Measure the hardware; do not trust the pinmap.** Its keypad matrix table
   was wrong in every position, and `PA11 "DEVICE POWER OFF"` does nothing.
   Labels marked `HW_PROBED` are guesses. `BINARY_VERIFIED` ones held up.
7. **Read Radtel's own source before theorising.** The RT-900 release answered
   both the flashing architecture and the power-off reset in minutes, after
   hours of reasoning in the wrong direction on each.
8. **A test whose pass and fail states look identical is not a test.** Blinky
   toggled a backlight over an empty framebuffer — black screen either way.
