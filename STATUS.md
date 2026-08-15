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

- Image layout settled: three regions, base 0x08003000, key block never programmed
- Channel record decoded and **selftest-verified**: 91/91 records re-encode
  byte-identically
- Zone names located at **0xC000** (see the correction in FINDINGS §4)
- Zone-enable state now persisted in spare `settings_t` bytes — the OEM's own
  copy at SRAM 0x2000A394 is rebuilt at boot and could not be reused
- Channel plan recovered from the radio, which was the only surviving copy —
  the Idaho/Utah/Nevada repeater list is back, round-tripping to zero byte diffs
- Function catalogue: 156 entries, recovered from Ghidra plate comments
- Firmware builds: text 39,876 / data 108 / bss 7,636
- **Knob picker + zones-as-filter implemented** on branch
  `feature/knob-picker-zone-filter`, including the firmware's first UI event
  dispatcher — nothing had ever called `event_poll()`, so input was being
  posted and discarded

## Hardware test, 2026-08-15 — custom firmware does NOT run on this radio

Flashed and tested. Result: the custom firmware boots but is unusable, and
**this is not caused by the picker/zone work**. Unmodified upstream `main`,
built with the same toolchain, fails identically. The feature branch is
exonerated; it has still never been meaningfully exercised.

Observed, both on the feature branch and on upstream `main`:

  splash screen renders correctly
  audio test tones play
  main screen is garbled
  no key tones, no power button, battery pull required to recover
  zero bytes of debug UART, on a DEBUG=1 build whose first act is a dbg_puts

The splash rendering correctly is the useful part: the LCD panel, timing and
driver all work, so the fault is above the display driver, not in it.

Everything still working is code that runs inside `main()` during init.
Everything dead is driven by a **scheduler task** — keypad, power button,
display refresh, UI. That points at `sched_run()` or its dispatch, but it could
not be narrowed further, because:

**RETRACTED: "this radio has no working debug UART."** That was wrong, and it
was my own tooling bug. `serial_monitor` in firmware_upload.py printed without
flushing; piped to a file, Python block-buffers at 8 KB, so a few hundred bytes
of boot trace never left the buffer — and killing the monitor with a signal
discarded it. Four empty captures were four empty *pipes*, not a silent radio.

The UART almost certainly worked the whole time. `dbg_init()` runs at the end
of `SystemInit` with the PLL already up (BRR 521 is correct for APB1 at
60 MHz), and it ends in `dbg_flush()` spinning on TC — since the splash screen
appears, that spin returned, which means the UART transmitted.

Fixed, and verified end-to-end against a virtual serial port: lines now arrive
promptly through a pipe. Diagnosing dead hardware from silence requires the
silence to be real.

Radio was restored to OEM V0.27 and is working. Channel data was never at risk:
it lives in external SPI flash, which firmware upload does not touch.

### Next on the radio

The feature branch **builds but has never run on hardware**. Worth testing in
this order, since each depends on the one before:

Do these in order — the first one gates everything else.

Instrumentation is fixed, so this is now one bootloader session. Four images
are prebuilt in `rt950-scratch/images/`; flash each with

    tools/flash_and_watch.sh images/<name>.BTF

which releases the port, uploads, and captures the trace to `logs/`.

1. **`01-feature-DEBUG.BTF`** — the real build. The trace answers everything at
   once: `[DBG] app_init complete` proves init finished, `[SCHED] run: tasks=11`
   proves the scheduler started, and repeating `[SCHED] hb t=` proves its loop
   turns. `[KBD_DIAG]` lines every 2 s show raw keypad GPIO; `[KEY] press:`
   appears if a key is actually detected.
2. If the scheduler runs but input is dead → **`02-hwtest9-keypad.BTF`**,
   which exercises keypad and encoder with nothing else running.
3. If the main screen is still garbled → **`03-hwtest3-lcd.BTF`** draws a test
   pattern, separating the display driver from `display_draw_main_screen()`.
4. **`04-hwtest11-diag.BTF`** is the full diagnostic if the picture is still
   unclear.

Only once the radio is functional does re-testing the picker mean anything:
does it open on the first detent without moving the highlight, does MENU commit
and retune, does `*` open the checklist, does a toggle survive a power cycle?

## Open

- **PR #2 needs updating.** It still contains the wrong 0xA200 zone address in
  its first commit, with a revert on top. Squash or re-open cleanly before
  asking Hertzz58 to merge — do not send a PR whose history proposes a
  regression and then undoes it.
- The Ghidra project's 53 stale `0x080xxxxx`-named functions are still there.
- `port_catalog.py` and `rf_register_match.py` are not yet rebuilt.
- Picker frequency mode is declared but not implemented; channel mode only.
- `*` opening the zone checklist is provisional; it belongs behind a Menu entry.
- Transmit power is at record byte 0x0E, low nibble (per Hertzz58's channel.h).
  Marked *derived*, not confirmed: every record in the dump holds the same
  value, so the dump cannot distinguish layouts. A dump of a radio programmed
  with mixed power levels would settle it.

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
