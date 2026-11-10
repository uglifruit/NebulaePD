# uf2: controls to a SuperCollider patch as OSC over UDP, Technobear-compatible: /neb/<name> <float> to port 3000.
# Same interface as pdsender.PdSend, so controlhandler's Pd branch drives it unchanged. Python 2 and 3 compatible.
#
# controlhandler hands over every value on every pass ("name value" strings, as for Pd). This sends a value when it
# changes, and all values again once a second, so a patch that starts late still learns the state. The triggers
# (reset, reset_alt) are sent only when they change, as in Technobear's firmware. One OSC bundle per pass.
import socket
import struct
import time

TRIGGERS = ("reset", "reset_alt")


def _pad(data):
    # OSC strings end with at least one NUL and are padded to a multiple of 4 bytes
    return data + b"\0" * (4 - len(data) % 4)


def osc_message(address, value):
    return _pad(address.encode("ascii")) + _pad(b",f") + struct.pack(">f", float(value))


def osc_bundle(messages):
    out = _pad(b"#bundle") + struct.pack(">Q", 1)       # time tag 1 = immediately
    for m in messages:
        out += struct.pack(">i", len(m)) + m
    return out


class ScSend(object):
    host = "127.0.0.1"
    sport = 3000
    resend_ms = 1000.0

    def __init__(self):
        self.sock = None
        self.connected = False
        self.last = {}
        self.last_full = -1e9
        self.connect()

    def connect(self):
        try:
            if self.sock is None:
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.connected = True
        except Exception:
            self.connected = False
        return self.connected

    def retry(self):
        return self.connected or self.connect()

    def is_connected(self):
        return self.connected

    def close(self):
        if self.sock is not None:
            try:
                self.sock.close()
            except Exception:
                pass
        self.sock = None
        self.connected = False
        self.last = {}
        self.last_full = -1e9

    def select(self, msgs, now_ms):
        """The (name, value) pairs to send this pass."""
        full = now_ms - self.last_full >= self.resend_ms
        if full:
            self.last_full = now_ms
        out = []
        for msg in msgs:
            parts = str(msg).split()
            if len(parts) != 2:
                continue
            try:
                value = float(parts[1])
            except ValueError:
                continue
            name = parts[0]
            if self.last.get(name) != value or (full and name not in TRIGGERS):
                out.append((name, value))
            self.last[name] = value
        return out

    def send(self, msgs):
        if not self.connected:
            return
        pairs = self.select(msgs, time.time() * 1000.0)
        if not pairs:
            return
        data = osc_bundle([osc_message("/neb/" + name, value) for name, value in pairs])
        try:
            self.sock.sendto(data, (self.host, self.sport))
        except Exception:
            pass    # UDP: nobody listening yet is fine, the next pass sends again
