# `REMIN:`/`REMOUT:` over AppleWin's Super Serial Card

A bidirectional text channel between the host and Apple Pascal running under
AppleWin, proven end to end (finding 210). Not wired into anything yet --
these are the two halves of the proof, kept so the next attempt starts from
a working round trip instead of from scratch.

```
python tools/remote/remresp.py 200      # host, start it FIRST
python tools/runemu.py --ssc            # guest, boots SYSHD with an SSC in slot 2
                                        # then X(ecute REMTEST at the Command level
```

`REMTEST.text` is the guest side: writes `HELLO` to `REMOUT:` (unit 8),
blocks on `UNITREAD` from `REMIN:` (unit 7) for eight characters, echoes
them back. `remresp.py` is the host side: waits for `HELLO`, replies
`PING4321`, checks the echo. Stage the source on `SYSHD:` with
`python tools/stagefile.py tools/remote/REMTEST.text REMTEST.TEXT` and
compile it with `emucompile.ps1 -Name REMTEST`.

## The four things that make or break it

**Poll-connect, never connect once.** AppleWin creates the listening socket
on port 1977 only when the guest first touches an SSC register. Nothing
exists to connect to before that, so a client that tries once and gives up
always loses the race. `remresp.py` retries every 200ms.

**A bound port is not a connected one, and the driver wants a connection.**
`CommStatus` reports DSR/CTS/DCD from the *accept* socket, so with the port
bound but nobody attached, DSR and DCD read inactive (they are active low,
so the status bits come back set) and Apple's `REMOUT:` driver waits for
carrier forever. This is what made finding 131 look like a hang inside the
driver. The status register reads `$70` unconnected and `$10` connected;
that difference is the whole diagnosis and it is easy to check by hand.

**The transmitter starts disabled.** After reset the ACIA command register
is `0`, which on a SY6551 means transmitter off, and AppleWin discards
writes in that state silently -- no error, no bytes. Pascal's own driver
initialises the card, so this only bites hand-written probes. From Applesoft
it is `POKE 49322,11` before `POKE 49320,<byte>`.

**Registry, not a switch.** `-s2 ssc` inserts the card but TCP mode comes
from `HKCU\Software\AppleWin\CurrentVersion\Configuration\Slot 2` ->
`Serial Port Name` = `TCP` (REG_SZ), read once in the card's constructor.
`runemu.py --ssc` writes it before launching. The port number, 1977, is
hardcoded in AppleWin.

## Checking it by hand, with no disks at all

An enhanced //e with every slot empty lands at the Applesoft `]` prompt, so
the card can be exercised with no Pascal and no media:

```
AppleWin.exe -model apple2ee -s2 ssc -s5 empty -s6 empty -s7 empty -power-on
PRINT PEEK(49321)     status  ($70 unconnected, $10 connected)
POKE 49323,30         control: 9600-8-N-1, internal clock
POKE 49322,11         command: DTR on, RX IRQ off, transmitter ENABLED
POKE 49320,65         transmit 'A'
```

## What is still not done

The console redirect itself. Finding 131 proved `REDIRIO` swaps `CONSOLE:`'s
read and write pointers through page zero (`RTPTR`=228, `WTPTR`=230) and
that the system really does go deaf and blind to the keyboard and screen
afterwards -- but that program was scratch and has been lost, so it needs
rewriting. With it, everything the system prints becomes text on the socket
and everything the host sends becomes keystrokes.

Two things to know before building that. `SYSTEM.STARTUP` runs
automatically at boot, so installing the redirect under that name arms the
channel with no keystrokes at all. And the swap lives in RAM with no way
back except killing the emulator and rebooting, so a run that wedges cannot
be rescued from the keyboard.
