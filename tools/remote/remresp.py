"""The host end of REMTEST: prove REMIN: carries bytes into the guest.

Poll-connects, because AppleWin creates the listening socket only when the
guest first touches an SSC register -- there is nothing to connect to until
REMTEST's own first UNITWRITE. Waits for HELLO, replies with eight bytes,
then reports what comes back.
"""
import socket
import sys
import time

PORT = 1977
REPLY = b'PING4321'
DEADLINE = float(sys.argv[1]) if len(sys.argv) > 1 else 180.0

start = time.monotonic()
sock = None
rx = bytearray()
sent = False


def stamp() -> str:
    return f'[{time.monotonic() - start:6.2f}s]'


while time.monotonic() - start < DEADLINE:
    if sock is None:
        s = socket.socket()
        s.settimeout(0.2)
        try:
            s.connect(('127.0.0.1', PORT))
        except OSError:
            s.close()
            time.sleep(0.2)
            continue
        sock = s
        print(f'{stamp()} connected', flush=True)

    try:
        data = sock.recv(4096)
    except socket.timeout:
        data = b''
    except OSError as exc:
        print(f'{stamp()} socket error: {exc}', flush=True)
        sock = None
        continue

    if data:
        rx += data
        print(f'{stamp()} rx {data!r}', flush=True)

    if not sent and b'HELLO' in rx:
        time.sleep(0.5)          # let the guest reach its UNITREAD
        sock.sendall(REPLY)
        sent = True
        print(f'{stamp()} tx {REPLY!r}', flush=True)

    if sent and rx.count(REPLY) >= 1 and len(rx) >= len(b'HELLO') + len(REPLY):
        print(f'{stamp()} echo received -- round trip complete', flush=True)
        break

print()
print(f'total received: {bytes(rx)!r}')
print(f'reply sent: {sent}')
if sent and REPLY in rx:
    print('VERDICT: both directions carry bytes, and the echo matches')
elif b'HELLO' in rx:
    print('VERDICT: REMOUT: works, REMIN: did NOT come back')
else:
    print('VERDICT: nothing arrived from the guest at all')
