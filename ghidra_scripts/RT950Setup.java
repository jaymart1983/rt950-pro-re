/* RT950Setup.java -- pre-analysis setup for the Radtel RT-950 Pro OEM firmware.
 *
 * Run as a headless preScript after importing the flat image (see
 * tools/build_flat_image.py) with the Binary loader at base 0x08003000 and
 * language ARM:LE:32:Cortex.
 *
 * Purpose: make pointer targets resolvable BEFORE auto-analysis. The inherited
 * project for this firmware was imported at 0x80000000, which left every
 * literal-pool value -- 0x0800xxxx flash pointers, 0x2000xxxx SRAM globals,
 * 0x4000xxxx peripheral registers -- outside any mapped block, so Ghidra created
 * no data cross-references and the entire data side stayed invisible.
 *
 * @category AT32/Setup
 */

import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.data.PointerDataType;
import ghidra.program.model.mem.Memory;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.symbol.SourceType;

public class RT950Setup extends GhidraScript {

    // name, start, end, read, write, execute
    private static final Object[][] BLOCKS = {
        {"SRAM",     0x20000000L, 0x20017FFFL, true, true,  true},
        {"BOOTROM",  0x1FFFB000L, 0x1FFFEFFFL, true, false, true},
        {"USD",      0x1FFFF800L, 0x1FFFF82FL, true, false, false},
        // APB1
        {"TMR2",  0x40000000L, 0x400003FFL, true, true, false},
        {"TMR3",  0x40000400L, 0x400007FFL, true, true, false},
        {"TMR4",  0x40000800L, 0x40000BFFL, true, true, false},
        {"TMR5",  0x40000C00L, 0x40000FFFL, true, true, false},
        {"TMR6",  0x40001000L, 0x400013FFL, true, true, false},
        {"TMR7",  0x40001400L, 0x400017FFL, true, true, false},
        {"TMR12", 0x40001800L, 0x40001BFFL, true, true, false},
        {"TMR13", 0x40001C00L, 0x40001FFFL, true, true, false},
        {"TMR14", 0x40002000L, 0x400023FFL, true, true, false},
        {"RTC",   0x40002800L, 0x40002BFFL, true, true, false},
        {"WWDT",  0x40002C00L, 0x40002FFFL, true, true, false},
        {"WDT",   0x40003000L, 0x400033FFL, true, true, false},
        {"SPI2",  0x40003800L, 0x40003BFFL, true, true, false},
        {"SPI3",  0x40003C00L, 0x40003FFFL, true, true, false},
        {"USART2",0x40004400L, 0x400047FFL, true, true, false},
        {"USART3",0x40004800L, 0x40004BFFL, true, true, false},
        {"UART4", 0x40004C00L, 0x40004FFFL, true, true, false},
        {"UART5", 0x40005000L, 0x400053FFL, true, true, false},
        {"I2C1",  0x40005400L, 0x400057FFL, true, true, false},
        {"I2C2",  0x40005800L, 0x40005BFFL, true, true, false},
        {"USBFS", 0x40005C00L, 0x40005FFFL, true, true, false},
        {"CAN1",  0x40006400L, 0x400067FFL, true, true, false},
        {"BPR",   0x40006C00L, 0x40006FFFL, true, true, false},
        {"PWC",   0x40007000L, 0x400073FFL, true, true, false},
        {"DAC",   0x40007400L, 0x400077FFL, true, true, false},
        // APB2
        {"IOMUX", 0x40010000L, 0x400103FFL, true, true, false},
        {"EXINT", 0x40010400L, 0x400107FFL, true, true, false},
        {"GPIOA", 0x40010800L, 0x40010BFFL, true, true, false},
        {"GPIOB", 0x40010C00L, 0x40010FFFL, true, true, false},
        {"GPIOC", 0x40011000L, 0x400113FFL, true, true, false},
        {"GPIOD", 0x40011400L, 0x400117FFL, true, true, false},
        {"GPIOE", 0x40011800L, 0x40011BFFL, true, true, false},
        {"ADC1",  0x40012400L, 0x400127FFL, true, true, false},
        {"ADC2",  0x40012800L, 0x40012BFFL, true, true, false},
        {"TMR1",  0x40012C00L, 0x40012FFFL, true, true, false},
        {"SPI1",  0x40013000L, 0x400133FFL, true, true, false},
        {"TMR8",  0x40013400L, 0x400137FFL, true, true, false},
        {"USART1",0x40013800L, 0x40013BFFL, true, true, false},
        {"ADC3",  0x40013C00L, 0x40013FFFL, true, true, false},
        {"TMR9",  0x40014C00L, 0x40014FFFL, true, true, false},
        {"TMR10", 0x40015000L, 0x400153FFL, true, true, false},
        {"TMR11", 0x40015400L, 0x400157FFL, true, true, false},
        {"I2C3",  0x40015C00L, 0x40015FFFL, true, true, false},
        {"SDIO1", 0x40018000L, 0x400183FFL, true, true, false},
        // AHB
        {"DMA1",     0x40020000L, 0x400203FFL, true, true, false},
        {"DMA2",     0x40020400L, 0x400207FFL, true, true, false},
        {"CRM",      0x40021000L, 0x400213FFL, true, true, false},
        {"FLASH_IF", 0x40022000L, 0x400223FFL, true, true, false},
        {"CRC",      0x40023000L, 0x400233FFL, true, true, false},
        {"XMC_REG",  0xA0000000L, 0xA0000FFFL, true, true, false},
        // Cortex-M4 private peripheral bus
        {"ITM",   0xE0000000L, 0xE0000FFFL, true, true, false},
        {"DWT",   0xE0001000L, 0xE0001FFFL, true, true, false},
        {"SCS",   0xE000E000L, 0xE000EFFFL, true, true, false},
        {"DEBUG", 0xE0042000L, 0xE00423FFL, true, true, false},
    };

    private static final String[] CORE_VECTORS = {
        "InitialSP", "Reset", "NMI", "HardFault", "MemManage", "BusFault",
        "UsageFault", "Reserved7", "Reserved8", "Reserved9", "Reserved10",
        "SVCall", "DebugMon", "Reserved13", "PendSV", "SysTick",
    };

    @Override
    public void run() throws Exception {
        Memory mem = currentProgram.getMemory();

        int made = 0, skipped = 0;
        for (Object[] b : BLOCKS) {
            String name = (String) b[0];
            long start = (Long) b[1], end = (Long) b[2];
            Address s = toAddr(start);
            if (mem.intersects(s, toAddr(end))) { skipped++; continue; }
            try {
                MemoryBlock blk = mem.createUninitializedBlock(name, s, end - start + 1, false);
                blk.setRead((Boolean) b[3]);
                blk.setWrite((Boolean) b[4]);
                blk.setExecute((Boolean) b[5]);
                blk.setVolatile(start >= 0x40000000L);   // MMIO: stop constant folding
                made++;
            } catch (Exception e) {
                println("[-] " + name + ": " + e.getMessage());
            }
        }
        println("[+] created " + made + " blocks, skipped " + skipped);

        /* Vector table. NOT getImageBase(): the Binary loader honours
         * -loader-baseAddr when placing the block but leaves the program's
         * image-base property at 0, which would send us to ram:00000000.
         * The firmware sets VTOR to 0x08003000 itself, which is the start of
         * the flat image. Override with RT950_VECBASE if analysing something
         * based elsewhere. */
        long vecBase = 0x08003000L;
        String vb = System.getenv("RT950_VECBASE");
        if (vb != null && !vb.isEmpty()) vecBase = Long.decode(vb.trim());

        Address vt = toAddr(vecBase);
        if (!mem.contains(vt)) {
            println("[-] no flash mapped at " + vt + "; skipping vector table");
            return;
        }
        println("[*] vector table at " + vt);
        createLabel(vt, "__initial_sp", true, SourceType.USER_DEFINED);

        int named = 0, rejected = 0;
        for (int i = 1; i < 112; i++) {
            Address slot = vt.add(i * 4L);
            if (!mem.contains(slot)) break;
            long target;
            try { target = getInt(slot) & 0xFFFFFFFFL; } catch (Exception e) { break; }
            if (target == 0) continue;
            if (target < 0x08000000L || target >= 0x08100000L || (target & 1) == 0) continue;

            try {
                clearListing(slot, slot.add(3));
                createData(slot, new PointerDataType());
            } catch (Exception e) { /* already typed */ }

            Address fn = toAddr(target & ~1L);
            int firstHalf;
            try { firstHalf = getShort(fn) & 0xFFFF; } catch (Exception e) { rejected++; continue; }

            /* Only name a vector whose target looks like a function entry. On a
             * wrongly-based image most slots point into the MIDDLE of other
             * functions, and naming those produced a listing full of bogus
             * "HardFault_Handler"s that were really fragments of app code.
             * Reset and the shared default handler legitimately have no
             * prologue, so those are allowed through. */
            boolean entry = (firstHalf & 0xFF00) == 0xB500 || (firstHalf & 0xFF00) == 0xB400
                         || firstHalf == 0xE92D || i == 1 || firstHalf == 0xE7FE
                         || (firstHalf & 0xF800) == 0x4800;

            String name = (i < CORE_VECTORS.length) ? CORE_VECTORS[i] + "_Handler"
                                                    : String.format("IRQ%d_Handler", i - 16);
            try {
                disassemble(fn);
                if (entry) {
                    createFunction(fn, name);
                    createLabel(fn, name, true, SourceType.USER_DEFINED);
                    named++;
                } else {
                    createFunction(fn, null);
                    rejected++;
                }
            } catch (Exception e) { rejected++; }
        }
        println("[+] vector table: " + named + " named, " + rejected + " rejected");

        Address reset = toAddr(getInt(vt.add(4)) & 0xFFFFFFFEL);
        addEntryPoint(reset);
        println("[+] entry point " + reset);
    }
}
