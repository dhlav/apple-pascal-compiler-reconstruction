"""Drive Apple Pascal over the REMIN:/REMOUT: socket, expect-style.

    python tools/remote/remdrive.py <seconds> [<pattern> <send>]...

Poll-connects to AppleWin's SSC on port 1977 (it has to poll -- AppleWin
creates the socket only when the guest first touches an SSC register, so
there is nothing to connect to until then), then walks the pattern/send
pairs in order: wait for the pattern to appear in everything received so
far, send the reply, move on. `\\r` in a reply is a carriage return, which
is what Apple Pascal's console reader wants -- not `\\n`.

Everything received is printed as it arrives, with control characters
shown, because a redirected Command level sends its own screen-control
bytes and those are data too. The exit status is 0 only if every step
matched.

This is a driver for experiments, not an acceptance-tier tool. It replaces
neither `emukeys.ps1` nor the screenshot path until the redirect itself is
trusted.
"""
import codecs
import socket
import sys
import time

PORT = 1977


def visible(data: bytes) -> str:
    out = []
    for b in data:
        if b in (13, 10):
            out.append('\\r' if b == 13 else '\\n')
        elif 32 <= b < 127:
            out.append(chr(b))
        else:
            out.append(f'<{b:02X}>')
    return ''.join(out)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    deadline = float(sys.argv[1])
    rest = sys.argv[2:]
    if len(rest) % 2:
        print('pattern/send arguments must come in pairs')
        return 2
    steps = [(rest[i], codecs.decode(rest[i + 1], 'unicode_escape'))
             for i in range(0, len(rest), 2)]

    start = time.monotonic()
    sock = None
    rx = bytearray()
    step = 0
    matched_at = len(rx)

    def stamp() -> str:
        return f'[{time.monotonic() - start:6.2f}s]'

    while time.monotonic() - start < deadline:
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
            print(f'{stamp()} << {visible(data)}', flush=True)

        if step < len(steps):
            pattern, reply = steps[step]
            # Match only in what arrived since the last step, so a prompt
            # that is still sitting in the log cannot satisfy two steps.
            if pattern.encode('ascii') in bytes(rx[matched_at:]):
                time.sleep(0.4)
                sock.sendall(reply.encode('ascii'))
                print(f'{stamp()} >> {visible(reply.encode("ascii"))}',
                      flush=True)
                matched_at = len(rx)
                step += 1

    print()
    print(f'steps completed: {step} of {len(steps)}')
    print(f'bytes received: {len(rx)}')
    if step < len(steps):
        print(f'STILL WAITING FOR: {steps[step][0]!r}')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
