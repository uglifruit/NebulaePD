#!/usr/bin/env python3
"""btkbd's safety checks against fake Pi 4 device trees (WSL: qemu-arm-static runs the real ARM binary).

  python3 bt/tests/test_btkbd_checks.py firmware/dist/bt/btkbd      (tools/btbuild.sh runs it after each build)

btkbd switches the Bluetooth chip's power through the Pi firmware's GPIO expander, whose other lines switch WiFi,
the power LED, a global reset and the SD card power. These tests prove it only ever picks the line the device tree
names BT_ON on the firmware expander, and refuses (touching nothing) in every doubtful case. With --root, btkbd
always stops after its checks, so no test can reach hardware.
"""
import os
import shutil
import struct
import subprocess
import sys
import tempfile

BTKBD = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "firmware/dist/bt/btkbd")
PI4_LINES = ["BT_ON", "WL_ON", "PWR_LED_OFF", "GLOBAL_RESET", "VDD_SD_IO_SEL", "CAM_GPIO", "SD_PWR_ON", "SD_OC_N"]


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data if isinstance(data, bytes) else data.encode())


def strlist(items):
    return b"".join(s.encode() + b"\0" for s in items)


def make_tree(root, model="Raspberry Pi 4 Model B Rev 1.5", cmdline="console=tty1 root=/dev/mmcblk0p2",
              lines=PI4_LINES, expander_compat="raspberrypi,firmware-gpio", second_expander=False, hci=False,
              pins=(32, 33), ctsrts=False, of_node="soc/serial@7e201000", hcds=("BCM4345C0.hcd",),
              serial1="/soc/serial@7e201000"):
    dt = root + "/proc/device-tree"
    write(dt + "/model", model + "\0")
    write(root + "/proc/cmdline", cmdline + "\n")
    write(dt + "/aliases/uart0", "/soc/serial@7e201000\0")
    write(dt + "/aliases/serial1", serial1 + "\0")
    # as the card's bcm2711-rpi-4-b.dtb: uart0_pins = <32 33> (TX/RX only)
    write(dt + "/soc/gpio@7e200000/uart0_pins/brcm,pins", b"".join(struct.pack(">I", p) for p in pins))
    # /dev/gpiomem: GPFSEL3 (GPIO 30..39); 32/33 ALT3 always, 30/31 ALT3 (CTS/RTS) only with ctsrts
    fsel3 = (7 << 6) | (7 << 9) | ((7 | (7 << 3)) if ctsrts else 0)
    regs = [0] * 1024
    regs[3] = fsel3
    write(root + "/dev/gpiomem", struct.pack("<1024I", *regs))
    # the SoC GPIO controller has line names too; a BT_ON here is not the expander and must be ignored
    write(dt + "/soc/gpio@7e200000/gpio-line-names", strlist(["ID_SDA", "ID_SCL", "BT_ON"]))
    write(dt + "/soc/gpio@7e200000/compatible", strlist(["brcm,bcm2711-gpio"]))
    write(dt + "/soc/firmware/gpio/gpio-line-names", strlist(lines))
    write(dt + "/soc/firmware/gpio/compatible", strlist([expander_compat]))
    if second_expander:
        write(dt + "/soc/firmware2/gpio/gpio-line-names", strlist(PI4_LINES))
        write(dt + "/soc/firmware2/gpio/compatible", strlist(["raspberrypi,firmware-gpio"]))
    os.makedirs(root + "/sys/class/bluetooth", exist_ok=True)
    if hci:
        os.makedirs(root + "/sys/class/bluetooth/hci0")
    tty = root + "/sys/class/tty/ttyAMA0/device"
    os.makedirs(tty, exist_ok=True)
    os.symlink("../../../../firmware/devicetree/base/" + of_node, tty + "/of_node")
    for h in hcds:
        write(root + "/usr/lib/firmware/updates/brcm/" + h, b"\x4c\xfc\x00")
    write(root + "/dev/vcio", b"")


CASES = [
    # (name, tree options, expected substring)
    ("Pi 4 as on the module (card's device tree)", {},
     "CHECKS OK: BT_ON = firmware GPIO 128, no flow control at 460800 baud, firmware"),
    ("CTS/RTS set up by the firmware", {"ctsrts": True},
     "CHECKS OK: BT_ON = firmware GPIO 128, flow control at 921600 baud"),
    ("BT_ON elsewhere on the expander", {"lines": ["WL_ON", "PWR_LED_OFF", "BT_ON"]}, "firmware GPIO 130"),
    ("Pi 4 specific firmware preferred", {"hcds": ("BCM4345C0.hcd", "BCM4345C0.raspberrypi,4-model-b.hcd")},
     "BCM4345C0.raspberrypi,4-model-b.hcd"),
    ("not a Pi 4", {"model": "Raspberry Pi 3 Model B Plus Rev 1.3"}, "FAIL: not a Raspberry Pi 4"),
    ("serial console on the BT UART", {"cmdline": "console=ttyAMA0,115200 root=/dev/mmcblk0p2"},
     "FAIL: a console is on the Bluetooth UART"),
    ("kernel already runs Bluetooth", {"hci": True}, "FAIL: the kernel already runs Bluetooth"),
    ("BT not on the PL011", {"serial1": "/soc/serial@7e215040"}, "FAIL: serial1 is not the PL011"),
    ("ttyAMA0 is another UART", {"of_node": "soc/serial@7e201400"}, "FAIL: /dev/ttyAMA0 is not uart0"),
    ("uart0 on the header pins", {"pins": (14, 15)}, "FAIL: uart0 is not on GPIO 32/33"),
    ("expander without its compatible", {"expander_compat": "something,else"}, "FAIL: no BT_ON line"),
    ("no BT_ON name at all", {"lines": PI4_LINES[1:]}, "FAIL: no BT_ON line"),
    ("two expanders name BT_ON", {"second_expander": True}, "FAIL: more than one BT_ON line"),
    ("BT_ON beyond the 8 lines", {"lines": ["L%d" % i for i in range(9)] + ["BT_ON"]},
     "FAIL: BT_ON is not one of the expander's 8 lines"),
    ("no firmware file", {"hcds": ()}, "FAIL: no BCM4345C0*.hcd"),
]


def run(root):
    cmd = ["qemu-arm-static", BTKBD, "--probe", "--root", root]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return r.returncode, r.stdout + r.stderr


def main():
    if not os.path.isfile(BTKBD):
        sys.exit("btkbd not found: " + BTKBD)
    bad = 0
    for name, opts, want in CASES:
        tmp = tempfile.mkdtemp(prefix="btkbd_dt_")
        try:
            make_tree(tmp, **opts)
            code, out = run(tmp)
        finally:
            shutil.rmtree(tmp)
        # refusals must say nothing was switched on; passes must name exactly the expected GPIO
        if want.startswith("FAIL"):
            ok = want.replace("FAIL: ", "PROBE FAIL: ") in out and "nothing was switched on" in out and code == 2
        else:
            ok = want in out and code == 0
        print("%s  %s" % ("ok  " if ok else "FAIL", name))
        if not ok:
            bad += 1
            print("      want: %s (exit %s)\n      got:\n%s" % (want, code, "\n".join("        " + l for l in
                                                                                    out.splitlines())))
    print("ALL OK" if not bad else "%d FAILED" % bad)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
