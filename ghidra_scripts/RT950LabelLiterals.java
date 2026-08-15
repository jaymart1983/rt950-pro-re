/* RT950LabelLiterals.java -- name the literal pool.
 *
 * Cortex-M code cannot embed a 32-bit constant in an instruction, so the
 * compiler parks constants in a literal pool near the function and emits
 * "ldr rN, [pc, #off]". Ghidra shows these as DAT_xxxxxxxx with no indication of
 * what they are. Since almost every global access and every peripheral touch
 * goes through one, an unlabelled pool means an unreadable listing.
 *
 * This walks every defined data item in flash that is referenced from code,
 * reads its 32-bit value, classifies it against the AT32F403A memory map, and
 * renames it accordingly:
 *
 *   0x2000xxxx -> LIT_SRAM_xxxxxxxx      pointer to a RAM global
 *   0x0800xxxx -> LIT_FLASH_xxxxxxxx     pointer to a flash table or string
 *   0x4001xxxx -> LIT_GPIOx_xxx          peripheral register, named by block
 *   0xE000xxxx -> LIT_SCS_xxx            core peripheral
 *
 * The last run classified 88.1% of pool slots and surfaced 170 distinct SRAM
 * globals and 131 flash tables. That census is what turned "some function
 * writing to DAT_08012a4c" into "the channel table".
 *
 * @category AT32/Naming
 */

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Data;
import ghidra.program.model.listing.DataIterator;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.Reference;
import ghidra.program.model.symbol.SourceType;

import java.util.*;

public class RT950LabelLiterals extends GhidraScript {

    private String classify(long v) {
        if (v >= 0x20000000L && v < 0x20018000L) return String.format("LIT_SRAM_%08X", v);
        if (v >= 0x08000000L && v < 0x08100000L) return String.format("LIT_FLASH_%08X", v);
        if (v >= 0x1FFFB000L && v < 0x20000000L) return String.format("LIT_SYSMEM_%08X", v);
        if (v >= 0x40000000L && v < 0x40030000L) {
            MemoryBlock b = currentProgram.getMemory().getBlock(toAddr(v));
            if (b != null) return String.format("LIT_%s_%03X", b.getName(),
                    v - b.getStart().getOffset());
            return String.format("LIT_PERIPH_%08X", v);
        }
        if (v >= 0xE0000000L) {
            MemoryBlock b = currentProgram.getMemory().getBlock(toAddr(v));
            if (b != null) return String.format("LIT_%s_%03X", b.getName(),
                    v - b.getStart().getOffset());
            return String.format("LIT_CORE_%08X", v);
        }
        return null;
    }

    @Override
    public void run() throws Exception {
        Map<String, Integer> kinds = new TreeMap<>();
        Set<Long> sramSeen = new TreeSet<>(), flashSeen = new TreeSet<>();
        int total = 0, named = 0, unclassified = 0;

        DataIterator it = currentProgram.getListing().getDefinedData(true);
        List<Data> pool = new ArrayList<>();
        while (it.hasNext()) {
            if (monitor.isCancelled()) break;
            Data d = it.next();
            if (d.getLength() != 4) continue;
            MemoryBlock b = currentProgram.getMemory().getBlock(d.getAddress());
            if (b == null || !b.isInitialized()) continue;
            long s = b.getStart().getOffset();
            if (s < 0x08000000L || s >= 0x08100000L) continue;
            // Only slots something actually loads from.
            Reference[] refs = getReferencesTo(d.getAddress());
            if (refs == null || refs.length == 0) continue;
            pool.add(d);
        }
        println("[*] " + pool.size() + " referenced 4-byte slots in flash");

        for (Data d : pool) {
            if (monitor.isCancelled()) break;
            total++;
            long v;
            try { v = getInt(d.getAddress()) & 0xFFFFFFFFL; } catch (Exception e) { continue; }

            String name = classify(v);
            if (name == null) { unclassified++; continue; }

            if (v >= 0x20000000L && v < 0x20018000L) sramSeen.add(v);
            else if (v >= 0x08000000L && v < 0x08100000L) flashSeen.add(v);
            kinds.merge(name.split("_")[1], 1, Integer::sum);

            /* Don't clobber a name a human already chose. */
            ghidra.program.model.symbol.Symbol sym =
                    currentProgram.getSymbolTable().getPrimarySymbol(d.getAddress());
            if (sym != null && sym.getSource() == SourceType.USER_DEFINED) continue;

            try {
                createLabel(d.getAddress(), name, true, SourceType.ANALYSIS);
                setEOLComment(d.getAddress(), String.format("-> %08X", v));
                named++;
            } catch (Exception e) { /* non-fatal */ }
        }

        println(String.format("[+] labelled %d/%d  (%.1f%% classified, %d unclassified)",
                named, total, total == 0 ? 0.0 : 100.0 * (total - unclassified) / total,
                unclassified));
        println("[+] distinct SRAM globals: " + sramSeen.size());
        println("[+] distinct flash targets: " + flashSeen.size());
        println("[*] by class:");
        for (Map.Entry<String, Integer> e : kinds.entrySet())
            println(String.format("    %-10s %d", e.getKey(), e.getValue()));
    }
}
