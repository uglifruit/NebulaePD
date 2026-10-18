#!/usr/bin/env python3
"""Mimic the Nebulae's PdSend: send 'name value;' FUDI messages to a Pd [netreceive 3000].

  python sim/send_fudi.py density 0.7 pitch 0.6
  python sim/send_fudi.py --sweep density      # 0..1..0 sweep
"""
import socket
import sys
import time

HOST, PORT = "localhost", 3000


def main(argv):
    s = socket.create_connection((HOST, PORT), timeout=2)
    if argv and argv[0] == "--sweep":
        name = argv[1]
        for v in list(range(0, 101, 2)) + list(range(100, -1, -2)):
            s.sendall(f"{name} {v / 100};".encode())
            time.sleep(0.02)
    else:
        if len(argv) % 2:
            sys.exit("usage: send_fudi.py name value [name value ...]")
        for n, v in zip(argv[::2], argv[1::2]):
            s.sendall(f"{n} {v};".encode())
    s.close()


if __name__ == "__main__":
    main(sys.argv[1:])
