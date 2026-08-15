/* RT950Export.java -- export analysis from the RT-950 Pro Ghidra project.
 *
 * Writes into $RT950_OUT (default /tmp/rt950_export):
 *   decompiled.c   every function, decompiled, in address order
 *   functions.csv  addr, name, size, params, callers, callees
 *   symbols.csv    the whole symbol table
 *   datarefs.csv   every data reference from code, with the target's block
 *   strings.csv    defined strings and who references them
 *
 * @category AT32/Export
 */

import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileOptions;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.address.Address;
import ghidra.program.model.data.StringDataInstance;
import ghidra.program.model.listing.*;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.*;

import java.io.File;
import java.io.PrintWriter;
import java.util.*;

public class RT950Export extends GhidraScript {

    private String csv(String s) {
        if (s == null) return "";
        return "\"" + s.replace("\"", "\"\"").replace("\n", " ").replace("\r", " ") + "\"";
    }

    private String blockOf(Address a) {
        if (a == null) return "";
        MemoryBlock b = currentProgram.getMemory().getBlock(a);
        return b == null ? "UNMAPPED" : b.getName();
    }

    @Override
    public void run() throws Exception {
        String outDir = System.getenv("RT950_OUT");
        if (outDir == null || outDir.isEmpty()) outDir = "/tmp/rt950_export";
        File dir = new File(outDir);
        dir.mkdirs();
        println("[*] exporting to " + dir.getAbsolutePath());

        FunctionManager fm = currentProgram.getFunctionManager();
        ReferenceManager rm = currentProgram.getReferenceManager();
        SymbolTable st = currentProgram.getSymbolTable();
        Listing listing = currentProgram.getListing();

        List<Function> funcs = new ArrayList<>();
        for (Function f : fm.getFunctions(true)) funcs.add(f);

        /* functions.csv first -- it is the cheap one and the catalogue depends on it */
        int named = 0;
        try (PrintWriter w = new PrintWriter(new File(dir, "functions.csv"))) {
            w.println("addr,name,size,params,n_callers,n_callees");
            for (Function f : funcs) {
                if (!f.getName().startsWith("FUN_")) named++;
                w.println(String.join(",",
                        f.getEntryPoint().toString(), csv(f.getName()),
                        String.valueOf(f.getBody().getNumAddresses()),
                        String.valueOf(f.getParameterCount()),
                        String.valueOf(f.getCallingFunctions(monitor).size()),
                        String.valueOf(f.getCalledFunctions(monitor).size())));
            }
        }
        println("[+] " + funcs.size() + " functions, " + named + " named");

        /* plate comments carry the catalogue's confidence/basis/notes text */
        int plates = 0;
        try (PrintWriter w = new PrintWriter(new File(dir, "plate_comments.csv"))) {
            w.println("addr,name,plate");
            for (Function f : funcs) {
                String p = listing.getComment(CodeUnit.PLATE_COMMENT, f.getEntryPoint());
                if (p != null && !p.isEmpty()) {
                    w.println(String.join(",", f.getEntryPoint().toString(),
                            csv(f.getName()), csv(p)));
                    plates++;
                }
            }
        }
        println("[+] " + plates + " plate comments (catalogue metadata)");

        try (PrintWriter w = new PrintWriter(new File(dir, "symbols.csv"))) {
            w.println("addr,name,type,block,source,ref_count");
            for (Symbol s : st.getAllSymbols(true)) {
                if (monitor.isCancelled()) break;
                w.println(String.join(",", s.getAddress().toString(), csv(s.getName()),
                        csv(s.getSymbolType().toString()), csv(blockOf(s.getAddress())),
                        csv(s.getSource().toString()),
                        String.valueOf(s.getReferenceCount())));
            }
        }

        int nref = 0;
        try (PrintWriter w = new PrintWriter(new File(dir, "datarefs.csv"))) {
            w.println("from_addr,from_func,to_addr,to_block,ref_type,to_symbol");
            for (Function f : funcs) {
                if (monitor.isCancelled()) break;
                for (Address a : f.getBody().getAddresses(true)) {
                    for (Reference ref : rm.getReferencesFrom(a)) {
                        if (!ref.getReferenceType().isData()) continue;
                        Address to = ref.getToAddress();
                        Symbol s = st.getPrimarySymbol(to);
                        w.println(String.join(",", a.toString(), csv(f.getName()),
                                to.toString(), csv(blockOf(to)),
                                csv(ref.getReferenceType().getName()),
                                csv(s == null ? "" : s.getName())));
                        nref++;
                    }
                }
            }
        }
        println("[+] " + nref + " data references");

        int nstr = 0;
        try (PrintWriter w = new PrintWriter(new File(dir, "strings.csv"))) {
            w.println("addr,length,n_refs,referrers,value");
            DataIterator it = listing.getDefinedData(true);
            while (it.hasNext()) {
                if (monitor.isCancelled()) break;
                Data d = it.next();
                if (!(d.getValue() instanceof String)) continue;
                StringDataInstance sdi = StringDataInstance.getStringDataInstance(d);
                if (sdi == StringDataInstance.NULL_INSTANCE) continue;
                String val = sdi.getStringValue();
                if (val == null || val.length() < 3) continue;
                List<String> from = new ArrayList<>();
                for (Reference r : rm.getReferencesTo(d.getAddress())) {
                    Function ff = fm.getFunctionContaining(r.getFromAddress());
                    from.add(ff == null ? r.getFromAddress().toString() : ff.getName());
                    if (from.size() >= 6) break;
                }
                w.println(String.join(",", d.getAddress().toString(),
                        String.valueOf(val.length()), String.valueOf(from.size()),
                        csv(String.join(" ", from)), csv(val)));
                nstr++;
            }
        }
        println("[+] " + nstr + " strings");

        DecompInterface di = new DecompInterface();
        di.setOptions(new DecompileOptions());
        di.toggleCCode(true);
        di.toggleSyntaxTree(true);
        di.setSimplificationStyle("decompile");
        if (!di.openProgram(currentProgram)) {
            println("[-] decompiler failed: " + di.getLastMessage());
            return;
        }
        int ok = 0, fail = 0;
        try (PrintWriter c = new PrintWriter(new File(dir, "decompiled.c"))) {
            for (Function f : funcs) {
                if (monitor.isCancelled()) break;
                DecompileResults r = di.decompileFunction(f, 90, monitor);
                if (r != null && r.decompileCompleted()) {
                    c.println("/* " + f.getEntryPoint() + "  " + f.getName() + " */");
                    c.println(r.getDecompiledFunction().getC());
                    ok++;
                } else fail++;
                if ((ok + fail) % 200 == 0) println("    " + (ok + fail) + "/" + funcs.size());
            }
        }
        di.dispose();
        println("[+] decompiled " + ok + " ok, " + fail + " failed");
        println("[*] export complete");
    }
}
