# TRCC Linux — Gap Analysis vs Windows C# Implementation

> Fresh audit 2026-02-18: every item verified against actual Python code by
> cross-referencing doc/audit/*.md (8 audit files, 53 C# source files).
>
> Method: 4 parallel agents each read one audit doc section, then searched
> the Python codebase for every documented C# feature. Only gaps are listed.

---

## OPEN — Verified Gaps

### 1. AK120 mask_size oversized (69 vs 64) — LOW
**Audit**: UCScreenLED.md §2 — LedCountVal3 = 64
**Code**: `led_segment.py:497` — `AK120Display.mask_size` returns 69
**Impact**: Harmless. Highest used index is 63 (USE_PARTIAL). Remap table has 64 entries → wire output is correct 192 bytes. Extra 5 mask entries are always False and ignored. Docstring also says "69-LED mask" — misleading.
**Fix**: Change `return 69` → `return 64`, update docstring.

### 2. LC1 mask_size oversized (38 vs 31) — LOW
**Audit**: UCScreenLED.md §2 — LedCountVal4 = 31
**Code**: `led_segment.py:564` — `LC1Display.mask_size` returns 38
**Impact**: Harmless. Highest used index is 30 (ALL_DIGITS). Remap table has 31 entries → wire output is correct 93 bytes. Extra 7 mask entries are always False and ignored.
**Fix**: Change `return 38` → `return 31`, update docstring.

### 3. Styles 9/12 zone_count=1 instead of 0 — LOW
**Audit**: FormLED.md §3 — LC2 (style 9) zone_count=0, LF13 (style 12) zone_count=0
**Code**: `models.py:480,483` — both have `zone_count=1`
**Impact**: Practically harmless. All zone logic guards on `zone_count > 1`, so zones list is never created and carousel never activates. But semantically wrong — C# treats these as zone-less styles.
**Fix**: Change `zone_count=1` → `zone_count=0` for styles 9 and 12 in `LED_STYLES`.

---

## HARDWARE LIMITATIONS — Cannot Fix (no Linux equivalent)

### 4. Memory clock sensor — no sysfs source
**Audit**: SystemInfo.md §7.1 — HWiNFO "Memory Clock"
**Code**: `sensors.py:666` — `mem_clock` mapped to empty string
**Impact**: LED memory info panel shows blank for clock. `dmidecode --type 17` gives static rated speed but no live frequency.

### 5. DRAM timing values (CAS/tRCD/tRP/tRAS/tRC/tRFC)
**Audit**: SystemInfo.md §7.1 — HWiNFO extracts from SPD
**Impact**: Only affects LED memory info panel. No Linux sysfs equivalent.

### 6. Memory clock ratio
**Audit**: SystemInfo.md §7.1 — HWiNFO "Memory Clock Ratio"
**Impact**: Niche metric with no Linux equivalent.

---

## WON'T FIX — By Design

### 7. Boot animation flash write (M7/M8)
**Audit**: FormCZTV.md — buttonFXTB_Click/GifTo565
**Reason**: Writing incorrect data to device flash could brick the boot animation. C# uses known-good embedded GIFs at exact resolutions — we don't have those resources. SCSI plumbing exists in `scsi.py` but intentionally not exposed.

### 8. GIF batch transfer to device flash
**Audit**: FormCZTV.md — GifTo565 multi-frame
**Reason**: Same flash-write risk as #7. Animated GIF playback works via host-side frame-by-frame transfer (video mode).

### 9. Fan LCD RPM feedback (FBL=54, PM=100)
**Audit**: FormCZTV.md — DeviceDataReceived, data[5]*30
**Reason**: Rare device. Requires new device-to-host USB read path. Fan RPM is read-only diagnostic — doesn't affect display functionality.

---

## NOT NEEDED — Windows-Only / Design Differences

- Shared memory IPC with USBLCD.exe — we talk USB directly
- Windows registry autostart — we use XDG .desktop
- .NET 6 installer button
- HWiNFO shared memory — we use native Linux sensors (sysfs/pynvml/psutil)
- WinForms DPI/memory management (GetDeviceCaps, EmptyWorkingSet)
- UCDongHuaLianDong, UCJianPanLianDongA/B/C — C# stubs (zero handlers, not functional)
- UCColorB/UCColorC inline pickers — replaced by QColorDialog
- UCShiJianXianShi/UCDingYiWenBen dedicated panels — covered by overlay grid
- Cloud download from czhorde.com — we use GitHub 7z archives
- FTP update check — we use PyPI
- Help opens PDF — we open GitHub docs
- FormKVMALED6 — unreleased/hidden code, not wired into Form1
- FormStart — splash screen, Linux GUI starts fast enough
- FormGetColor screen pixel sampler — replaced by QColorDialog + EyedropperOverlay
- LED settings binary format (0xDC header) — we use JSON (cleaner, cross-platform)
- Window drag via custom cmd 241/242/243 — Qt has native window drag
- Per-core sensor filtering — extra sensors visible on Linux, no functional impact

---

## Summary

| Category | Count | Severity |
|----------|-------|----------|
| Open gaps | 3 | All LOW (no wrong data to device) |
| Hardware limits | 3 | Cannot fix (no Linux equivalent) |
| Won't fix | 3 | By design (liability/rare device) |
| Not needed | 16 | Windows-only or design difference |
| **Verified correct** | **Everything else** | All 4 protocols, 6 LED effects, 12 remap tables, overlay system, theme system, screencast, video, sensors, API, CLI, GUI |
