/* RT950FindFunctions.java -- recover functions Ghidra's auto-analysis missed.
 *
 * Auto-analysis found 373 functions in the RT-950 Pro image. Scanning for the
 * targets of Thumb-2 BL instructions took that to 970. The gap exists because
 * auto-analysis walks forward from entry points; anything reached only through a
 * table, or sitting in a region it declined to disassemble, never gets visited.
 *
 * Thumb-2 BL is a 32-bit instruction in two halfwords:
 *   hw1  1111 0 S imm10            (0xF000 mask 0xF800)
 *   hw2  11 J1 1 J2 imm11          (0xD000 mask 0xD000)
 * The offset is sign-extended 25-bit, and J1/J2 are stored XORed with S:
 *   I1 = ~(J1^S), I2 = ~(J2^S)
 *   offset = S:I1:I2:imm10:imm11:0
 * Getting that XOR wrong yields targets that are wrong by megabytes and land
 * outside flash, so a bad decoder fails loudly rather than silently.
 *
 * @category AT32/Analysis
 */

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryBlock;

import java.util.*;

public class RT950FindFunctions extends GhidraScript {

    @Override
    public void run() throws Exception {
        Memory mem = currentProgram.getMemory();

        // The flash block: initialised, executable, based at 0x08xxxxxx.
        MemoryBlock flash = null;
        for (MemoryBlock b : mem.getBlocks()) {
            long s = b.getStart().getOffset();
            if (b.isInitialized() && b.isExecute() && s >= 0x08000000L && s < 0x08100000L) {
                if (flash == null || b.getSize() > flash.getSize()) flash = b;
            }
        }
        if (flash == null) { println("[-] no flash block found"); return; }

        long lo = flash.getStart().getOffset(), hi = flash.getEnd().getOffset();
        println(String.format("[*] scanning %s  %08X-%08X (%d KiB)",
                flash.getName(), lo, hi, (hi - lo + 1) / 1024));

        int before = currentProgram.getFunctionManager().getFunctionCount();

        Map<Long, Integer> hits = new HashMap<>();   // target -> BL count
        long scanned = 0, decoded = 0;

        for (long a = lo; a + 3 <= hi; a += 2) {
            if (monitor.isCancelled()) break;
            scanned++;
            int hw1, hw2;
            try {
                hw1 = getShort(toAddr(a)) & 0xFFFF;
                if ((hw1 & 0xF800) != 0xF000) continue;
                hw2 = getShort(toAddr(a + 2)) & 0xFFFF;
            } catch (Exception e) { continue; }
            if ((hw2 & 0xD000) != 0xD000) continue;   // BL, not BLX/B.W

            int S     = (hw1 >> 10) & 1;
            int imm10 = hw1 & 0x3FF;
            int J1    = (hw2 >> 13) & 1;
            int J2    = (hw2 >> 11) & 1;
            int imm11 = hw2 & 0x7FF;
            int I1 = (~(J1 ^ S)) & 1;
            int I2 = (~(J2 ^ S)) & 1;

            int off = (S << 24) | (I1 << 23) | (I2 << 22) | (imm10 << 12) | (imm11 << 1);
            if (S != 0) off |= 0xFE000000;            // sign-extend from bit 24

            long target = a + 4 + off;
            if (target < lo || target > hi || (target & 1) != 0) continue;
            decoded++;
            hits.merge(target, 1, Integer::sum);
        }

        println(String.format("[+] scanned %d halfwords, %d BL targets, %d distinct",
                scanned, decoded, hits.size()));

        // Most-called first: those are the library routines, and defining them
        // before their callers keeps the decompiler from inlining them badly.
        List<Map.Entry<Long, Integer>> sorted = new ArrayList<>(hits.entrySet());
        sorted.sort((x, y) -> y.getValue() - x.getValue());

        int created = 0, existed = 0, failed = 0;
        for (Map.Entry<Long, Integer> e : sorted) {
            if (monitor.isCancelled()) break;
            Address t = toAddr(e.getKey());
            Function f = getFunctionAt(t);
            if (f != null) { existed++; continue; }
            try {
                if (getInstructionAt(t) == null) disassemble(t);
                if (createFunction(t, null) != null) created++; else failed++;
            } catch (Exception ex) { failed++; }
        }

        int after = currentProgram.getFunctionManager().getFunctionCount();
        println(String.format("[+] created %d, already defined %d, failed %d", created, existed, failed));
        println(String.format("[+] function count %d -> %d", before, after));

        // Top call targets are worth naming by hand first.
        println("[*] most-referenced targets:");
        for (int i = 0; i < Math.min(15, sorted.size()); i++) {
            Map.Entry<Long, Integer> e = sorted.get(i);
            Function f = getFunctionAt(toAddr(e.getKey()));
            println(String.format("    %08X  %4d calls  %s", e.getKey(), e.getValue(),
                    f == null ? "(none)" : f.getName()));
        }
    }
}
