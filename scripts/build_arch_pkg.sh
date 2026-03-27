#!/usr/bin/env bash
# Build a local Arch Linux .pkg.tar.zst from the current source tree.
# Run from the repo root: bash scripts/build_arch_pkg.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# ── Version ─────────────────────────────────────────────────────────────────
VER=$(python -c "import sys; sys.path.insert(0,'src'); from trcc.__version__ import __version__; print(__version__)")
echo "=== Building trcc-linux ${VER} ==="

# ── Paths ────────────────────────────────────────────────────────────────────
PKG=/tmp/trcc-pkg-root
OUTPUT="$REPO_ROOT/packages"
ARCHPKG="$OUTPUT/trcc-linux-${VER}-1-any.pkg.tar.zst"

rm -rf "$PKG"
mkdir -p "$PKG/usr" "$OUTPUT"

# ── Step 1: Build wheel ──────────────────────────────────────────────────────
echo "--- Building wheel ---"
python -m build --wheel --no-isolation

WHL=$(ls "$REPO_ROOT"/dist/trcc_linux-*.whl | sort -V | tail -1)
echo "    Wheel: $WHL"

# ── Step 2: Install into staging directory ───────────────────────────────────
echo "--- Installing into staging dir ---"
python -m installer --destdir="$PKG" --prefix=/usr "$WHL"

# ── Step 3: Fix shebangs ─────────────────────────────────────────────────────
echo "--- Fixing shebangs ---"
find "$PKG" -name "trcc*" -path "*/bin/*" \
    -exec sed -i "1s|^#\!.*/python[0-9.]*|#!/usr/bin/python|" {} +

# ── Step 4: Bundle uvicorn (not in official Arch repos) ──────────────────────
echo "--- Bundling uvicorn ---"
pip install --root="$PKG" --prefix=/usr --no-deps uvicorn

# ── Step 5: Install packaging assets ─────────────────────────────────────────
echo "--- Installing assets ---"
install -Dm644 packaging/udev/99-trcc-lcd.rules \
    "$PKG/usr/lib/udev/rules.d/99-trcc-lcd.rules"
install -Dm644 packaging/modprobe/trcc-lcd.conf \
    "$PKG/usr/lib/modprobe.d/trcc-lcd.conf"
install -Dm644 packaging/modprobe/trcc-sg.conf \
    "$PKG/usr/lib/modules-load.d/trcc-sg.conf"
install -Dm644 src/trcc/assets/trcc-linux.desktop \
    "$PKG/usr/share/applications/trcc-linux.desktop"
for size in 256 128 64 48 32 24 16; do
    install -Dm644 "src/trcc/assets/icons/trcc_${size}x${size}.png" \
        "$PKG/usr/share/icons/hicolor/${size}x${size}/apps/trcc.png"
done
install -Dm644 src/trcc/assets/com.github.lexonight1.trcc.policy \
    "$PKG/usr/share/polkit-1/actions/com.github.lexonight1.trcc.policy"
install -Dm644 src/trcc/assets/trcc-quirk-fix.service \
    "$PKG/usr/lib/systemd/system/trcc-quirk-fix.service"
install -Dm644 LICENSE \
    "$PKG/usr/share/licenses/trcc-linux/LICENSE"

# ── Step 6: Write .PKGINFO ────────────────────────────────────────────────────
echo "--- Writing .PKGINFO ---"
INSTALLED_SIZE=$(du -sk "$PKG" | cut -f1)
cat > "$PKG/.PKGINFO" << INFO
pkgname = trcc-linux
pkgver = ${VER}-1
pkgdesc = Thermalright LCD/LED Control Center for Linux
url = https://github.com/jemte/thermalright-trcc-linux
builddate = $(date +%s)
packager = TRCC Linux CI <ci@email.com>
size = ${INSTALLED_SIZE}
arch = any
license = GPL-3.0-or-later
depend = python
depend = pyside6
depend = python-numpy
depend = python-psutil
depend = python-pyusb
depend = python-click
depend = python-typer
depend = python-fastapi
depend = libusb
depend = sg3_utils
depend = p7zip
optdepend = python-pynvml: NVIDIA GPU sensor support
optdepend = python-dbus: Wayland session support
optdepend = python-gobject: Wayland session support
optdepend = python-hidapi: Alternative HID transport
INFO

# ── Step 7: Create archive ────────────────────────────────────────────────────
echo "--- Creating .pkg.tar.zst ---"
cd "$PKG"
tar -cf - .PKGINFO * | zstd -o "$ARCHPKG"
cd "$REPO_ROOT"

# ── Step 8: Verify ────────────────────────────────────────────────────────────
echo "=== Arch Verification ==="
echo "  Package: $ARCHPKG ($(du -h "$ARCHPKG" | cut -f1))"
echo "  Entry points:"
tar -tf "$ARCHPKG" | grep "usr/bin/" || echo "  (no entry points found)"
echo "=== Build PASSED ==="
