/* RT950ApplyNames.java -- apply the function catalogue to the Ghidra database.
 *
 * Reads out/Function_Names_extended.csv and, for each row, renames the function
 * and writes a plate comment holding the row's subsystem, confidence, purpose,
 * basis and notes.
 *
 * The plate comment is not decoration. It is the catalogue's second copy: when
 * the working tree was destroyed, RT950Export reconstructed all 156 entries by
 * parsing these comments back out of the analysis database. Keep the field
 * labels byte-identical to the parser in tools/recover_catalog.py.
 *
 * Two failures worth not repeating:
 *
 *  1. This script twice carried a hardcoded absolute path to the CSV. After the
 *     project directory was renamed, and again after it moved, it applied ZERO
 *     names while still exiting 0 -- so the run "succeeded" and the listing was
 *     untouched. The path is now resolved relative to the script, and a missing
 *     file throws. Verify a run by the named-function COUNT, never by exit code.
 *
 *  2. A column was once inserted in the middle of the CSV, shifting every field
 *     right, which produced 53 functions literally named "0x080xxxxx" with
 *     garbled plate comments. Columns are therefore addressed BY HEADER NAME
 *     here, not by index, so adding a column cannot silently corrupt a run.
 *
 * @category AT32/Naming
 */

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.CodeUnit;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.SourceType;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.*;

public class RT950ApplyNames extends GhidraScript {

    /* Minimal RFC4180 splitter: quoted fields, "" for a literal quote. */
    private static List<String> splitCsv(String line) {
        List<String> out = new ArrayList<>();
        StringBuilder cur = new StringBuilder();
        boolean q = false;
        for (int i = 0; i < line.length(); i++) {
            char c = line.charAt(i);
            if (q) {
                if (c == '"') {
                    if (i + 1 < line.length() && line.charAt(i + 1) == '"') { cur.append('"'); i++; }
                    else q = false;
                } else cur.append(c);
            } else if (c == '"') q = true;
            else if (c == ',') { out.add(cur.toString()); cur.setLength(0); }
            else cur.append(c);
        }
        out.add(cur.toString());
        return out;
    }

    private static String sanitise(String n) {
        String s = n.trim().replaceAll("[^A-Za-z0-9_]", "_");
        if (s.isEmpty()) return null;
        if (Character.isDigit(s.charAt(0))) s = "_" + s;
        return s;
    }

    @Override
    public void run() throws Exception {
        /* getSourceFile() returns a Ghidra ResourceFile, NOT a java.io.File --
         * assigning it directly compiles against the wrong type and dies at
         * runtime with ClassNotFoundException. */
        File scriptDir = new File(getSourceFile().getAbsolutePath()).getParentFile();
        File csv = new File(scriptDir.getParentFile(), "out/Function_Names_extended.csv");

        String override = System.getenv("RT950_CATALOG");
        if (override != null && !override.isEmpty()) csv = new File(override);

        if (!csv.isFile()) {
            throw new IllegalStateException("catalogue not found: " + csv.getAbsolutePath()
                    + "  (set RT950_CATALOG to override)");
        }
        println("[*] catalogue: " + csv.getAbsolutePath());

        List<String> lines = Files.readAllLines(csv.toPath(), StandardCharsets.UTF_8);
        if (lines.isEmpty()) throw new IllegalStateException("catalogue is empty");

        /* Address columns by header name. */
        List<String> hdr = splitCsv(lines.get(0));
        Map<String, Integer> col = new HashMap<>();
        for (int i = 0; i < hdr.size(); i++) col.put(hdr.get(i).trim().toLowerCase(), i);
        for (String need : new String[]{"real_addr", "proposed_name"}) {
            if (!col.containsKey(need))
                throw new IllegalStateException("catalogue missing required column: " + need);
        }

        int renamed = 0, commented = 0, notFound = 0, badRow = 0, badAddr = 0;
        List<String> misses = new ArrayList<>();

        for (int ln = 1; ln < lines.size(); ln++) {
            if (monitor.isCancelled()) break;
            String raw = lines.get(ln);
            if (raw.trim().isEmpty()) continue;
            List<String> f = splitCsv(raw);

            String addrS = f.size() > col.get("real_addr") ? f.get(col.get("real_addr")).trim() : "";
            String name  = f.size() > col.get("proposed_name") ? f.get(col.get("proposed_name")).trim() : "";
            if (addrS.isEmpty() || name.isEmpty()) { badRow++; continue; }

            /* Guard against the column-shift bug resurfacing: a proposed_name
             * that is itself an address means the row is misaligned. */
            if (name.matches("(?i)^0x[0-9a-f]{8}$")) {
                println("[-] line " + (ln + 1) + ": name looks like an address (" + name
                        + ") -- columns misaligned, skipping");
                badRow++;
                continue;
            }

            Address a;
            try {
                a = toAddr(Long.decode(addrS.startsWith("0x") || addrS.startsWith("0X")
                        ? addrS : "0x" + addrS));
            } catch (Exception e) { badAddr++; continue; }

            Function fn = getFunctionAt(a);
            if (fn == null) fn = getFunctionContaining(a);
            if (fn == null) { notFound++; misses.add(addrS + " " + name); continue; }

            String safe = sanitise(name);
            if (safe == null) { badRow++; continue; }
            try {
                fn.setName(safe, SourceType.USER_DEFINED);
                renamed++;
            } catch (Exception e) {
                println("[-] rename " + addrS + " -> " + safe + ": " + e.getMessage());
            }

            /* Field labels here are a parsing contract -- see header. */
            StringBuilder p = new StringBuilder();
            p.append(safe).append("\n");
            for (String[] fieldLabel : new String[][]{
                    {"subsystem", "subsystem "}, {"confidence", "confidence"},
                    {"purpose", "purpose   "}, {"basis", "basis     "},
                    {"notes", "notes     "}}) {
                Integer ci = col.get(fieldLabel[0]);
                if (ci == null || f.size() <= ci) continue;
                String v = f.get(ci).trim();
                if (v.isEmpty()) continue;
                p.append(fieldLabel[1]).append(": ").append(v).append("\n");
            }
            try {
                setPlateComment(fn.getEntryPoint(), p.toString());
                commented++;
            } catch (Exception e) { /* non-fatal */ }
        }

        println(String.format("[+] renamed %d, plate comments %d", renamed, commented));
        println(String.format("[+] skipped: %d no function, %d bad row, %d bad address",
                notFound, badRow, badAddr));
        for (String m : misses.subList(0, Math.min(12, misses.size()))) println("    miss " + m);

        /* Report the count the way it should be verified. */
        int named = 0, total = 0;
        for (Function fn : currentProgram.getFunctionManager().getFunctions(true)) {
            total++;
            if (!fn.getName().startsWith("FUN_")) named++;
        }
        println(String.format("[=] %d/%d functions now named", named, total));

        if (renamed == 0) {
            throw new IllegalStateException(
                    "applied zero names -- this is the silent-failure mode, treat as an error");
        }
    }
}
