# Courtesy of hecanjob/pippi.pd
# uf1: one sendall() per batch instead of one send() per message (same FUDI bytes), and a non-blocking-ish
# connect() that the control handler retries until Pd is listening.
import socket
import time
class PdSend():
    pdhost = 'localhost'
    #pdhost = "192.168.0.33"
    sport = 3000
    rport = 3001
    pd = None
    connected = False
    retry_ms = 250
    last_attempt = 0

    def __init__(self):
        self.connect()

    def connect(self):
        print('connecting to pd')
        self.last_attempt = time.time() * 1000.0
        try:
            if self.pd is not None:
                self.pd.close()
            self.pd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            print("created socket.")
            self.pd.settimeout(0.5)
            self.pd.connect((self.pdhost, self.sport))
            self.pd.settimeout(None)
            self.connected = True
            print('Sending to PD on port ' + str(self.sport))

        except:
            self.connected = False
            # close now: a timed-out attempt must not complete later behind our back (Windows keeps retrying)
            try:
                self.pd.close()
            except:
                pass
            self.pd = None
            print('Connection failed - open PD with [netreceive ' + str(self.sport) + '] at least!')
        return self.connected

    def retry(self):
        # Called every poll while Pd mode has no connection; attempts at most every retry_ms.
        if self.connected:
            return True
        if time.time() * 1000.0 - self.last_attempt < self.retry_ms:
            return False
        return self.connect()

    def batch(self, msgs):
        data = ''.join([str(msg) + ';' for msg in msgs])
        if not isinstance(data, bytes): # Python 3 (tests); a no-op on the module's Python 2
            data = data.encode('ascii')
        return data

    def send(self, msgs):
        try:
            self.pd.sendall(self.batch(msgs))
        except:
            if self.connected:
                print('Lost connection to PD.')
            self.connected = False
            print('Could not send. Did you open a connection?')

    def close(self):
        print('Closing connection to PD')
        if self.pd is not None:
            self.pd.close()
        self.connected = False

    def format(self, target, val):
        msg = target + ' ' + str(val)
        return msg

    def is_connected(self):
        return self.connected
