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

## Next on the radio

The feature branch **builds but has never run on hardware**. Worth testing in
this order, since each depends on the one before:

1. Does `task_ui` drain the queue without starving anything? It is the first
   consumer the queue has ever had.
2. Does the picker open on the first detent and NOT move the highlight?
3. Does MENU commit and actually retune? `ui_commit_channel` calls
   `channel_to_vfo`, which is not verified.
4. Does `*` open the checklist, and does toggling survive a power cycle?

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
