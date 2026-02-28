"""Shared USB device lifecycle helpers for bulk-class transports.

Eliminates duplication between BulkDevice and LyDevice — both use the same
find → detach → configure → claim sequence.  Protocol-specific endpoint
detection stays in each subclass.
"""

from __future__ import annotations

import logging
import time
from typing import Any

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers (not exported — used only by open_usb_device)
# ---------------------------------------------------------------------------

_ERR_NOT_FOUND = "USB device {vid:04x}:{pid:04x} not found"
_ERR_NOT_FOUND_RESET = "USB device {vid:04x}:{pid:04x} not found after reset"
_ERR_SELINUX = (
    "USB interface busy — SELinux is blocking USB device access. "
    "Run 'sudo trcc setup-selinux' to install the policy module, "
    "then unplug and replug the device."
)


def _find_vendor_interface(cfg: Any) -> Any:
    """Prefer vendor-specific interface (bInterfaceClass=255), fallback to (0,0)."""
    for candidate in cfg:
        if candidate.bInterfaceClass == 255:  # type: ignore[union-attr]
            return candidate
    return cfg[(0, 0)]  # type: ignore[index]


def _detach_kernel_drivers(dev: Any, count: int = 4) -> bool:
    """Detach kernel drivers from interfaces 0..count-1.

    Returns True if SELinux blocking was detected (driver still active
    after detach attempt).
    """
    import usb.core  # type: ignore[import-untyped]

    selinux_blocked = False
    for i in range(count):
        try:
            if not dev.is_kernel_driver_active(i):  # type: ignore[union-attr]
                continue
            dev.detach_kernel_driver(i)  # type: ignore[union-attr]
            # Verify detach actually worked (SELinux silently blocks it)
            if dev.is_kernel_driver_active(i):  # type: ignore[union-attr]
                selinux_blocked = True
                log.warning("Kernel driver still active on interface %d after "
                            "detach — SELinux may be blocking USB ioctls", i)
            else:
                log.debug("Detached kernel driver from interface %d", i)
        except usb.core.USBError as e:
            log.debug("Could not detach kernel driver from interface %d: %s", i, e)
            try:
                if dev.is_kernel_driver_active(i):  # type: ignore[union-attr]
                    selinux_blocked = True
                    log.warning("Kernel driver still active on interface %d "
                                "after detach error — SELinux may be blocking", i)
            except (usb.core.USBError, NotImplementedError):
                pass
        except NotImplementedError:
            pass
    return selinux_blocked


def _reset_and_refind(dev: Any, vid: int, pid: int) -> Any:
    """Reset USB device, wait, re-find, detach drivers. Returns new handle."""
    import usb.core  # type: ignore[import-untyped]

    dev.reset()  # type: ignore[union-attr]
    time.sleep(0.5)
    new_dev = usb.core.find(idVendor=vid, idProduct=pid)
    if new_dev is None:
        raise RuntimeError(_ERR_NOT_FOUND_RESET.format(vid=vid, pid=pid))
    _detach_kernel_drivers(new_dev)
    return new_dev


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def open_usb_device(vid: int, pid: int) -> tuple[Any, Any]:
    """Find, configure, and claim a vendor-class USB device.

    Handles the full USB lifecycle:
      find → detach kernel drivers (SELinux-aware) → configure
      → find vendor interface → claim (with EBUSY retry) → return

    Returns:
        (device, interface) tuple ready for endpoint detection.

    Raises:
        RuntimeError: Device not found, or SELinux blocking.
        usb.core.USBError: Permission denied (errno 13).
    """
    import usb.core  # type: ignore[import-untyped]
    import usb.util  # type: ignore[import-untyped]

    dev = usb.core.find(idVendor=vid, idProduct=pid)
    if dev is None:
        raise RuntimeError(_ERR_NOT_FOUND.format(vid=vid, pid=pid))

    # 1. Detach kernel drivers (SELinux post-verification included)
    selinux_blocked = _detach_kernel_drivers(dev)

    # 2. Configure device (skip if already configured — SELinux safety)
    try:
        cfg = dev.get_active_configuration()  # type: ignore[union-attr]
        log.debug("Device already configured, skipping set_configuration()")
    except usb.core.USBError as e:
        if e.errno == 13:  # EACCES — permission denied
            raise
        log.debug("No active configuration, calling set_configuration()")
        try:
            dev.set_configuration()  # type: ignore[union-attr]
        except usb.core.USBError:
            log.warning("set_configuration() failed, resetting device and retrying")
            dev = _reset_and_refind(dev, vid, pid)
            dev.set_configuration()  # type: ignore[union-attr]
        cfg = dev.get_active_configuration()  # type: ignore[union-attr]

    # 3. Find vendor-specific interface
    intf = _find_vendor_interface(cfg)

    # 4. Claim interface (with EBUSY retry)
    try:
        usb.util.claim_interface(dev, intf.bInterfaceNumber)  # type: ignore[union-attr]
    except usb.core.USBError as e:
        if e.errno != 16:  # Not EBUSY
            raise
        if selinux_blocked:
            raise RuntimeError(_ERR_SELINUX) from e
        log.warning("claim_interface() EBUSY — resetting device and retrying")
        dev = _reset_and_refind(dev, vid, pid)
        cfg = dev.get_active_configuration()  # type: ignore[union-attr]
        intf = _find_vendor_interface(cfg)
        usb.util.claim_interface(dev, intf.bInterfaceNumber)  # type: ignore[union-attr]

    return dev, intf
