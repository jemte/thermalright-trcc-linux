# Supported Devices

## Confirmed Working

These devices have been tested on real hardware and confirmed working with TRCC Linux.

### Full LCD Screen (Custom Themes, Images, Videos, Overlays)

| Product | Connection | Screen | Tested By |
|---------|-----------|--------|-----------|
| FROZEN HORIZON PRO | SCSI (87CD:70DB) | 320x320 | Developer |
| FROZEN MAGIC PRO | SCSI (87CD:70DB) | 320x320 | Developer |
| FROZEN VISION V2 | SCSI (87CD:70DB) | 320x320 | Developer |
| FROZEN WARFRAME | SCSI (0402:3922) | 320x320 | Developer |
| FROZEN WARFRAME SE | SCSI (0402:3922) | 320x320 | Developer |
| LC1, LC2, LC3, LC5 | SCSI (0416:5406) | 320x320 | Developer |
| GrandVision 360 AIO | Bulk (87AD:70DB) | 480x480 | [bipobuilt](https://github.com/bipobuilt) |
| Mjolnir Vision 360 | Bulk (87AD:70DB) | 480x480 | [Pikarz](https://github.com/Pikarz) |
| Trofeo Vision LCD | HID (0416:5302) | 1280x480 | [PantherX12max](https://github.com/PantherX12max) |

### LED + Segment Display (RGB Fan Control, Temperature Readout)

| Product | Connection | Tested By |
|---------|-----------|-----------|
| HR10 2280 PRO Digital | HID (0416:8001) | [Lcstyle](https://github.com/Lcstyle) |
| AX120 Digital | HID (0416:8001) | [shadowepaxeor-glitch](https://github.com/shadowepaxeor-glitch), [hexskrew](https://github.com/hexskrew) |
| Peerless Assassin 120 Digital ARGB White | HID (0416:8001) | [Xentrino](https://github.com/Xentrino) |
| Phantom Spirit 120 Digital EVO | HID (0416:8001) | [javisaman](https://github.com/javisaman) |

---

## In Progress (Tester-Reported, Fixes Pending)

These devices have been reported by testers and are being actively debugged.

### HID LCD Devices

| Product | Connection | Issue | Status |
|---------|-----------|-------|--------|
| Frozen Warframe 360 | HID (0416:5302) | [#28](https://github.com/Lexonight1/thermalright-trcc-linux/issues/28) | Color + rotation fix in v5.0.8, awaiting confirmation |
| Assassin Spirit 120 Vision ARGB | HID (0416:5302) | [#16](https://github.com/Lexonight1/thermalright-trcc-linux/issues/16) | Same fix as #28 (v5.0.8), awaiting confirmation |
| Assassin Spirit 120 Vision | HID (0416:5302) | [#32](https://github.com/Lexonight1/thermalright-trcc-linux/issues/32) | Udev setup needed, awaiting response |

### SCSI Devices

| Product | Connection | Issue | Status |
|---------|-----------|-------|--------|
| FROZEN WARFRAME 240 | SCSI (0402:3922) | [#17](https://github.com/Lexonight1/thermalright-trcc-linux/issues/17) | FBL=100 mismatch (320x320 vs 320x240 panel), investigating |

### LED Devices

| Product | Connection | Issue | Status |
|---------|-----------|-------|--------|
| PA120 Digital | HID (0416:8001) | [#15](https://github.com/Lexonight1/thermalright-trcc-linux/issues/15) | Display turns off after 10s, investigating |

---

## Need Testers

These products are recognized by the Windows TRCC app and should work with TRCC Linux. If you own one of these, we'd love your help testing — run `trcc report` and [open an issue](https://github.com/Lexonight1/thermalright-trcc-linux/issues).

### Full LCD Screen Products (Vision Series)

These have a full pixel LCD (240x240 to 1920x462) for custom themes, images, videos, and sensor overlays.

| Product | Chinese Name |
|---------|-------------|
| Frozen Vision V2 | 冰封视界 V2 |
| Core Vision | 核芯视界 |
| Core Matrix VISION | 矩阵视界 |
| Mjolnir Vision PRO | 雷神之锤 PRO |
| Elite Vision | 精英视界 |
| Hyper Vision | 终越视界 |
| Stream Vision | 风擎视界 |
| Rainbow Vision | 彩虹视界 |
| Peerless Vision | 无双视界 |
| Levita Vision | 悠浮视界 |
| TL-M10 VISION | — |
| TR-A70 Vision | — |
| AS120 VISION | — |
| BA120 VISION | — |
| Burst Assassin 120 Vision | — |
| Peerless Assassin 120 Vision | — |
| Royal Lord 120 Vision | — |
| Royal Knight 130 Vision | — |
| Phantom Spirit 120 Vision | — |
| Magic Qube | — |

### LED + Segment Display Products (Digital Series)

These have a small digital display showing CPU/GPU temperature plus addressable RGB LED fans.

| Product |
|---------|
| Peerless Assassin 140 Digital |
| Frozen Magic Digital |
| Royal Knight 120 Digital |
| Royal Knight 130 Digital |
| MC-3 DIGITAL |

---

## USB Interfaces

All devices connect through one of these USB VID:PIDs:

| VID:PID | Protocol | Display | Products |
|---------|----------|---------|----------|
| 87CD:70DB | SCSI | Full LCD | Older LCD screens |
| 87AD:70DB | Bulk | Full LCD | GrandVision 360 AIO, Mjolnir Vision 360 |
| 0402:3922 | SCSI | Full LCD | Frozen Warframe series (360/SE/PRO/Ultra) |
| 0416:5406 | SCSI | Full LCD | Winbond LCD variant |
| 0416:5302 | HID Type 2 | Full LCD | Vision/Warframe (newer HW) |
| 0418:5303 | HID Type 3 | Full LCD | TARAN ARMS |
| 0418:5304 | HID Type 3 | Full LCD | TARAN ARMS |
| 0416:8001 | HID | LED + segment / Full LCD | Digital series + many Vision products |

The exact product model is identified after a USB handshake. The device responds with PM (product model) and SUB bytes that tell the app which product it is and whether to show the LCD or LED control panel.

## How to Help Test

If you own any of the untested devices above and run Linux:

1. Install: `pip install trcc-linux`
2. Run the setup wizard: `trcc setup` (checks deps, installs udev rules, desktop entry)
3. Unplug/replug USB cable
4. Run detection: `trcc detect --all`
5. Try the GUI: `trcc gui`
6. Report what you see at https://github.com/Lexonight1/thermalright-trcc-linux/issues
