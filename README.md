# RT-950 Pro — reverse engineering notes and tooling

Analysis notes, tooling and channel-planning scripts for the **Radtel RT-950 Pro**
(Artery AT32F403A, dual BK4829, SI4732, ST7789V 240x320).

This repository holds **only original work**: analysis tooling, documented findings and
channel data. It deliberately contains no OEM firmware images, no decompiler output and no
per-unit calibration data — those are derivative works of Radtel's copyrighted firmware, or
specific to one radio, and stay off GitHub.

## Layout

| path | contents |
|---|---|
| `ghidra_scripts/` | Java GhidraScripts: memory map, function recovery, name application, export |
| `tools/` | Python: image layout, channel encode/decode, cross-version catalogue porting |
| `out/Function_Names_extended.csv` | the function catalogue — name, address, confidence, evidence |
| `out/*.md` | structural findings: channel records, SRAM map, state machine, specs |
| `FINDINGS.md` | the main writeup, including retractions |
| `STATUS.md` | current state and open threads — start here |

## Related

* Firmware work: [jaymart1983/Radtel-RT950-Pro-Firmware](https://github.com/jaymart1983/Radtel-RT950-Pro-Firmware),
  a fork of [Hertzz58/Radtel-RT950-Pro-Firmware](https://github.com/Hertzz58/Radtel-RT950-Pro-Firmware) (GPLv3)
* Reference: [DualTachyon/radtel-rt-890-oefw](https://github.com/DualTachyon/radtel-rt-890-oefw) (Apache 2.0) —
  the RT-890 shares BK4819/BK4829 silicon and, in many cases, literal register constants

## Method note

Confidence levels are meant literally. `High` means proved from disassembly or an exact match
against known-good reference code; `Low` means the name comes from a function's shape alone.
Several entries record corrections to earlier conclusions, including my own — those are kept
rather than quietly edited, because knowing which claims moved is part of the evidence.
