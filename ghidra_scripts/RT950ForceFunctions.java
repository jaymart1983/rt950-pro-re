/* RT950ForceFunctions.java -- recover functions reached only indirectly.
 *
 * RT950FindFunctions catches everything called by a direct BL. It cannot catch
 * anything dispatched through a register -- and this firmware leans on that
 * heavily, because it drives two different transceivers (BK4819 and BK4829)
 * through an ops table. Those handlers are only ever reached via BLX Rn, so no
 * BL anywhere in the image points at them.
 *
 * Two passes:
 *   1. Scan the whole image for words that look like Thumb code pointers
 *      (0x08xxxxx1, in range, odd). Runs of >= 3 consecutive such words are
 *      almost certainly a dispatch table -- isolated matches are usually just
 *      constants that happen to look like pointers, so they are ignored.
 *   2. Sweep gaps between defined functions for orphan code, since a handler
 *      whose table lives in a region Ghidra typed as data leaves a hole.
 *
 * @category AT32/Analysis
 */

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.SourceType;

import java.util.*;

public class RT950ForceFunctions extends GhidraScript {

    private static final int MIN_RUN = 3;

    @Override
    public void run() throws Exception {
        Memory mem = currentProgram.getMemory();

        MemoryBlock flash = null;
        for (MemoryBlock b : mem.getBlocks()) {
            long s = b.getStart().getOffset();
            if (b.isInitialized() && b.isExecute() && s >= 0x08000000L && s < 0x08100000L) {
                if (flash == null || b.getSize() > flash.getSize()) flash = b;
            }
        }
        if (flash == null) { println("[-] no flash block"); return; }
        long lo = flash.getStart().getOffset(), hi = flash.getEnd().getOffset();

        int before = currentProgram.getFunctionManager().getFunctionCount();

        /* Pass 1: pointer tables. */
        List<long[]> tables = new ArrayList<>();   // {start, count}
        Set<Long> targets = new LinkedHashSet<>();
        long runStart = -1; int run = 0;

        for (long a = lo & ~3L; a + 3 <= hi; a += 4) {
            if (monitor.isCancelled()) break;
            long v;
            try { v = getInt(toAddr(a)) & 0xFFFFFFFFL; } catch (Exception e) { v = 0; }
            boolean ptr = (v & 1) == 1 && (v & ~1L) >= lo && (v & ~1L) <= hi;
            if (ptr) {
                if (run == 0) runStart = a;
                run++;
            } else {
                if (run >= MIN_RUN) {
                    tables.add(new long[]{runStart, run});
                    for (int i = 0; i < run; i++) {
                        try { targets.add(getInt(toAddr(runStart + i * 4L)) & 0xFFFFFFFEL); }
                        catch (Exception e) { /* skip */ }
                    }
                }
                run = 0;
            }
        }
        if (run >= MIN_RUN) {
            tables.add(new long[]{runStart, run});
            for (int i = 0; i < run; i++) {
                try { targets.add(getInt(toAddr(runStart + i * 4L)) & 0xFFFFFFFEL); }
                catch (Exception e) { /* skip */ }
            }
        }

        println(String.format("[+] %d candidate dispatch tables, %d distinct targets",
                tables.size(), targets.size()));
        tables.sort((x, y) -> Long.compare(y[1], x[1]));
        for (int i = 0; i < Math.min(10, tables.size()); i++) {
            println(String.format("    %08X  %d entries", tables.get(i)[0], tables.get(i)[1]));
        }

        int made = 0, had = 0, failed = 0;
        for (long t : targets) {
            if (monitor.isCancelled()) break;
            Address a = toAddr(t);
            if (getFunctionAt(a) != null) { had++; continue; }
            try {
                if (getInstructionAt(a) == null) disassemble(a);
                if (createFunction(a, null) != null) made++; else failed++;
            } catch (Exception e) { failed++; }
        }
        println(String.format("[+] table targets: %d created, %d existed, %d failed", made, had, failed));

        /* Label the tables so they are recognisable in the listing. */
        int lbl = 0;
        for (long[] t : tables) {
            try {
                createLabel(toAddr(t[0]), String.format("PTRTAB_%08X_%d", t[0], t[1]),
                        true, SourceType.ANALYSIS);
                lbl++;
            } catch (Exception e) { /* already labelled */ }
        }
        println("[+] labelled " + lbl + " tables");

        /* Pass 2: orphan code in the gaps between defined functions. */
        List<Function> fns = new ArrayList<>();
        for (Function f : currentProgram.getFunctionManager().getFunctions(true)) fns.add(f);
        fns.sort(Comparator.comparing(Function::getEntryPoint));

        int orphan = 0;
        for (int i = 0; i + 1 < fns.size(); i++) {
            if (monitor.isCancelled()) break;
            long end = fns.get(i).getBody().getMaxAddress().getOffset() + 1;
            long next = fns.get(i + 1).getEntryPoint().getOffset();
            if (next - end < 4 || next - end > 0x800) continue;   // huge gaps are data

            for (long a = (end + 1) & ~1L; a + 1 < next; a += 2) {
                int hw;
                try { hw = getShort(toAddr(a)) & 0xFFFF; } catch (Exception e) { break; }
                // push {..., lr} / push {..} / stmdb sp!
                if ((hw & 0xFF00) != 0xB500 && (hw & 0xFF00) != 0xB400 && hw != 0xE92D) continue;
                Address at = toAddr(a);
                if (getFunctionContaining(at) != null) continue;
                try {
                    if (getInstructionAt(at) == null) disassemble(at);
                    if (createFunction(at, null) != null) { orphan++; break; }
                } catch (Exception e) { /* keep scanning the gap */ }
            }
        }
        println("[+] " + orphan + " orphan functions recovered from gaps");

        int after = currentProgram.getFunctionManager().getFunctionCount();
        println(String.format("[+] function count %d -> %d", before, after));
    }
}
