#!/usr/bin/env python3
"""Print per-50 ms peak levels of a WAV (handles Pd's 32-bit float WAVs). Used to check test renders.

  python tools/wavpeaks.py out.wav [more.wav ...]
"""
import struct
import sys


def readwav(path):
    b = open(path, "rb").read()
    i, fmt, data = 12, None, b""
    while i + 8 <= len(b):
        cid = b[i:i + 4]
        sz = struct.unpack("<I", b[i + 4:i + 8])[0]
        body = b[i + 8:i + 8 + sz]
        if cid == b"fmt ":
            fmt = struct.unpack("<HHIIHH", body[:16])
        elif cid == b"data":
            data = body
        i += 8 + sz + (sz & 1)
    tag, ch, sr, _, _, bits = fmt
    if tag == 0xFFFE:  # WAVE_FORMAT_EXTENSIBLE: real format is in the subformat GUID
        tag = 3 if bits == 32 and b"\x03\x00\x00\x00\x00\x00\x10\x00" in b[:200] else 1
    n = len(data) // (bits // 8)
    if tag == 3:
        vals = struct.unpack("<%df" % n, data[:n * 4])
    elif bits == 16:
        vals = [v / 32768 for v in struct.unpack("<%dh" % n, data[:n * 2])]
    else:
        vals = [v / 2 ** 31 for v in struct.unpack("<%di" % n, data[:n * 4])]
    return ch, sr, vals


def main():
    for p in sys.argv[1:]:
        ch, sr, v = readwav(p)
        print(p, "sr", sr, "frames", len(v) // ch)
        seg = int(0.05 * sr)
        for c in range(ch):
            x = v[c::ch]
            out = []
            for s in range(0, len(x), seg):
                pk = max(abs(t) for t in x[s:s + seg])
                if pk > 1e-4:
                    out.append(f"{s / sr:.2f}s:{pk:.3f}")
            print(f"  ch{c + 1}", " ".join(out[:200]))


if __name__ == "__main__":
    main()
