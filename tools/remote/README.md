# `REMIN:`/`REMOUT:` over AppleWin's Super Serial Card

A bidirectional text channel between the host and Apple Pascal running under
AppleWin. **The whole system -- Command level, Filer, compiler -- can be
driven over it, with the keyboard and screen dead** (findings 210, 211). Not
wired into the acceptance tier yet; `emucompile.ps1` and the screenshot path
are untouched.

```
python tools/remote/remdrive.py 170 "Command:" "F" "Filer:" "L" ...   # host, FIRST
python tools/runemu.py --ssc                                          # guest
                                                                      # then X REDIRIO
```

`REDIRIO.text` is the one that matters: it swaps `CONSOLE:`'s and
`SYSTERM:`'s entries in the system's page-zero device tables for
`REMIN:`'s and `REMOUT:`'s, so everything the system prints goes to the
socket and everything the host sends arrives as keystrokes. It is a
**toggle** -- running it a second time, over the socket, puts the console
back, which is the only recovery short of a reboot. It prints the whole
unit table before acting, so every run re-probes the addresses it depends
on rather than trusting them.

`remdrive.py` is the host end: poll-connects, logs everything with control
characters visible, and walks pattern/send pairs expect-style. An empty
pattern fires immediately, which is how you answer a prompt that was
already on screen before you connected.

`REMTEST.text` is the smaller proof underneath: writes `HELLO` to `REMOUT:`
(unit 8), blocks on `UNITREAD` from `REMIN:` (unit 7), echoes the eight
characters back. `remresp.py` drives it. Worth keeping because it isolates
the transport from the redirect -- if `REDIRIO` ever goes quiet, run this
first to find out which half broke.

Stage either source on `SYSHD:` with
`python tools/stagefile.py tools/remote/REDIRIO.text REDIRIO.TEXT` and
compile it with `emucompile.ps1 -Name REDIRIO`.

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

## The device tables, re-probed on every run

Page zero `228` (`RTPTR`) and `230` (`WTPTR`) hold the base addresses of two
tables of eight 2-byte routine addresses, one entry per unit, so unit N sits
at `base + 2*(N-1)`. `REDIRIO` prints the whole thing before it acts, so
every run re-measures what it is about to change. Unchanged from finding
131:

```
RTPTR=-2850  WTPTR=-2866
  unit 1 read=-256  write=-253   CONSOLE:
  unit 2 read=-256  write=-253   SYSTERM:   same routines, separate entries
  unit 3 read=   0  write=-223   GRAPHIC:
  unit 4 read=   0  write=   0   DISK1:     block device, not in this table
  unit 5 read=   0  write=   0   DISK2:
  unit 6 read=   0  write=-247   PRINTER:   write-only, so its read slot is free
  unit 7 read=-232  write=   0   REMIN:     read-only, so its write slot is free
  unit 8 read=   0  write=-229   REMOUT:
```

Units 1 and 2 share the same two routines but are separate entries, and the
system uses `SYSTERM:` for unechoed reads, so **both have to be swapped** --
changing only unit 1 leaves a live keyboard behind and makes the result
impossible to interpret. The two permanently-unused slots, unit 6's read and
unit 7's write, hold the saved originals; both read back `0` on an untouched
system, which is also how `REDIRIO` knows which way to toggle.

## What is still not done

Wiring it into the acceptance tier. `emucompile.ps1` still drives a compile
with SendKeys and captures a screenshot. Going over this channel instead
would give compile output as *text* -- error numbers and line numbers read
rather than eyeballed -- with no foreground-window requirement and no
60ms-per-key pacing.

Two things to know before that. `SYSTEM.STARTUP` runs automatically at
boot, so installing `REDIRIO.CODE` under that name would arm the channel
with no keystrokes at all. And the swap lives in RAM, so a run that wedges
before the toggle can be sent has to be killed and rebooted -- cheap in
itself, but it means every acceptance run would then depend on this
working.
