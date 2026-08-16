# RT-950 Pro — status

Start here. Updated 2026-08-15.

## Where things live

| what | where |
|---|---|
| RE notes, catalogue, tooling | `github.com/jaymart1983/rt950-pro-re` (this repo) |
| Custom firmware | `github.com/jaymart1983/Radtel-RT950-Pro-Firmware`, fork of Hertzz58 |
| Radio dump | `out/radio_dump_v029/` — **local only**, not committed |
| RT-900 vendor source | `rt900/` — **local only**, no licence |
| Ghidra exports | `ghidra_out_true/` — **local only**, derivative work |

The ARM toolchain is at `~/.local/arm-none-eabi/bin`. Add it to PATH:

```bash
export PATH="$HOME/.local/arm-none-eabi/bin:$PATH"
```

It was extracted from the package Homebrew downloaded, because
`brew install --cask gcc-arm-embedded` needs an admin password. If you would
rather have it installed system-wide, run that cask install yourself.

## Done

### Reverse engineering
- Image layout settled: three regions, base 0x08003000, key block never programmed
- Channel record **selftest-verified**: 91/91 records re-encode byte-identically
- Zone names located at **0xC000** (see the correction in FINDINGS §4)
- Channel plan recovered from the radio — the Idaho/Utah/Nevada repeater list is
  back, round-tripping to zero byte differences
- Function catalogue: 156 entries, recovered from Ghidra plate comments

### Firmware — verified on hardware
| subsystem | state |
|---|---|
| LCD + text + geometry + RGB565 | working, flicker-free redraw |
| UART debug | working |
| Zero-touch flashing | working, repeatable |
| Encoder | one detent per click |
| Keypad | all 20 keys |
| SPI flash | reads channel data byte-identical to the dump |
| Power off/on | STOP mode, EXTI wake, immediate |
| Audio | tone + volume + keypad beeps |
| LEDs (PC13 red / PC14 green) | working |
| **BK4829 x2** | **both report REG00=4829, independently addressable** |
| **GPS** | **397 NMEA sentences in 30 s** |
| **Battery ADC** | **fixed: was reading the wrong channel** |
| SI4732 | power-up fixed; GET_REV still wrong |

The **in-app updater** is the significant piece: the bootloader has no soft
entry, so the application programs its own flash the way Radtel's RT-900 does.
Reflashing needs no buttons and no battery pull.

`hw_init()` is now shared with the HW_TEST builds. Three subsystems previously
looked broken purely because tests skipped it and the scheduler.

## Open
- **PR #2** on Hertzz58's repo — the two build fixes. Unchanged.
- The knob picker and zone filter are written but have **never executed**. They
  predate everything above working.
- No true hardware power cut found. Current "off" is STOP mode, not an unpowered
  radio. Remaining lead: the OEM decompile (see FINDINGS §8.7).
- **The SPI flash is not what the code assumed.** JEDEC 5E 40 16: a different
  manufacturer, and capacity byte 0x16 = 4 MB, not the 2 MB W25Q16 documented.
  Confirmed non-destructively (0x200000 does not alias to 0x000000). Something
  already occupies 0x200000, written by neither this firmware nor anything we
  know of — worth identifying.
- **SI4732 GET_REV** returns status 0x1F (CTS clear) and part number 0x00
  instead of 0x32. A one-byte status read shows CTS set — that is why power-up
  now passes — while the nine-byte response read does not, so suspicion is on
  the multi-byte read path, not the chip.
- **adc_read_audio_level()** reads channel 1, which is the battery. Channel 4 is
  the likelier audio candidate but is unconfirmed, so it is flagged rather than
  moved on a guess.
- Untested subsystems: speaker/audio, BK4829 transceivers, battery ADC, SI4732,
  GPS.
- `port_catalog.py` and `rf_register_match.py` still not rebuilt.

## Watch out

1. **Power-cycle the radio after every channel write.** It caches the list at
   boot; a stale display looks exactly like a failed write.
2. **Run `--selftest` before writing anything to the radio.** It has caught two
   real encoder faults.
3. **Verify naming runs by counting named functions**, not by exit status. The
   apply script has silently applied zero names twice while exiting 0.
4. **Do not trust the RT-900 source for absolute addresses.** Structure yes,
   addresses no. See FINDINGS §4.
5. **This machine's filesystem is case-insensitive.** `rm -rf rt950-pro` deleted
   `RT950-Pro`. That is how the working tree was lost. Everything that matters
   is now pushed to GitHub; keep it that way.
