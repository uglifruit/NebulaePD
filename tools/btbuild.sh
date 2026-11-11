#!/bin/sh
# Build btkbd (bt/btkbd, the Nebulae's Bluetooth keyboard) in WSL, from a pinned BTstack release.
#   wsl -u andy -- sh /mnt/c/Users/andyu/Documents/NebulaePD/tools/btbuild.sh
# Needs arm-linux-gnueabihf-gcc (apt: gcc-arm-linux-gnueabihf) and git. Output: firmware/dist/bt/btkbd (static
# armv7 hard-float binary, so the module's glibc 2.35 doesn't matter) and its sha256. Also builds and runs the native
# keymap unit test. Two runs give the same sha256 (no timestamps, build ids or build paths in the binary).
# BTstack licence: free for personal, non-commercial use only (its LICENSE, condition 4).
set -e
BTSTACK_URL=https://github.com/bluekitchen/btstack.git
BTSTACK_COMMIT=51e11ce3692abfe31b4ee3d66cffdeb1ae1626f2   # tag v1.8.3
REPO=$(cd "$(dirname "$0")/.." && pwd)
SRC="$REPO/bt/btkbd"
OUT="$REPO/firmware/dist/bt"
BTSTACK="$HOME/btstack"
WORK="$HOME/btkbd_build"

if [ ! -d "$BTSTACK/.git" ]; then git clone -q "$BTSTACK_URL" "$BTSTACK"; fi
cd "$BTSTACK"
git cat-file -e "$BTSTACK_COMMIT^{commit}" 2>/dev/null || git fetch -q --tags origin
git -c advice.detachedHead=false checkout -q "$BTSTACK_COMMIT"
test -z "$(git status --porcelain)" || { echo "BTstack checkout has local changes"; exit 1; }

rm -rf "$WORK"
mkdir -p "$WORK" "$OUT"
cd "$WORK"
make -s -f "$SRC/Makefile" keymap_test CC=gcc BTSTACK_ROOT="$BTSTACK"
./keymap_test
make -s -j4 -f "$SRC/Makefile" btkbd BTSTACK_ROOT="$BTSTACK"
arm-linux-gnueabihf-strip btkbd
cp btkbd "$OUT/btkbd"
file "$OUT/btkbd"
ls -l "$OUT/btkbd"
cd "$OUT" && sha256sum btkbd | tee btkbd.sha256
echo "BTstack $BTSTACK_COMMIT ($(cd "$BTSTACK" && git describe --tags))"
# the safety checks against fake Pi 4 device trees (qemu-arm-static: apt install qemu-user-static)
python3 "$REPO/bt/tests/test_btkbd_checks.py" "$OUT/btkbd"
