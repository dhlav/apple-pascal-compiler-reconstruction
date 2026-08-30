"""Poll a window's screen region, diff frames, and OCR whatever changed.

Built for driving AppleWin unattended: `emukeys.ps1` already knows how to
send keystrokes and take one screenshot, but deciding *when* to send the
next keystroke, or whether a compile/assemble/link has finished, has always
meant a human looking at the emulator. This script is the other half --
it captures the window every `--interval` seconds (default 0.5), diffs
each frame against the last one, and OCRs only the frames that changed, so
a caller (or another agent) can watch stdout and react instead of guessing
a fixed `-Wait`.

Capture uses the same method `emukeys.ps1` already validated for AppleWin
specifically: `GetWindowRect` + a screen-coordinate grab, not `PrintWindow`
(AppleWin is GDI/DirectX and does not answer `WM_PRINT` correctly). Unlike
`emukeys.ps1`, this does *not* require AppleWin to be foreground to
capture -- it is a spectator, meant to run continuously while something
else (a human, or `emukeys.ps1`) drives focus and keys. Each reported
frame's JSON carries `"foreground": true/false` so a caller can tell
whether the capture might have been occluded by another window, the one
failure mode `emukeys.ps1` refuses outright and this script only flags.

Output is JSON Lines on stdout, one object per event, flushed immediately:

    {"event": "watch_start", "hwnd": 132456, "title": "AppleWin Emulator"}
    {"event": "change", "t": 1.5, "foreground": true, "text": "]CSYSHD:..."}
    {"event": "idle", "t": 4.5}

`text` is a normal JSON string -- `json.dumps` escapes control characters
and newlines for you, which is both "escape it out" and what keeps each
event on exactly one line for a line-based reader (`Monitor`, `tail -f`,
a pipe). Nothing here needs uuencoding on top of that.

An `"idle"` event fires once, the first poll where `--idle-after` seconds
(default 3.0 -- 6 polls at the default 0.5s interval) have passed with no
change; it does not repeat every poll after that, only the next "change"
resets it. Deciding whether an idle screen means "done" or "stuck waiting
for input" is left to the caller -- this script only reports what changed
and when it stopped changing, the same split of responsibility as
`emukeys.ps1` leaving "what to type next" to its caller.

Window selection is one `--window` argument, tried in order:
  1. all-digits -> treated as a raw HWND if `IsWindow` accepts it, else a PID
  2. otherwise -> case-insensitive substring match against either the
     process's image name (`AppleWin.exe`) or the window's title text
Default is "AppleWin", matching `emukeys.ps1`'s own `Get-Process AppleWin`.

    python tools/watchscreen.py
    python tools/watchscreen.py --window AppleWin --interval 0.5 --idle-after 3
    python tools/watchscreen.py --once --save-dir build/watch
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pytesseract
import win32api
import win32gui
import win32process
from PIL import Image, ImageChops, ImageGrab

TESSERACT_EXE = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
if TESSERACT_EXE.exists():
    pytesseract.pytesseract.tesseract_cmd = str(TESSERACT_EXE)

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def _process_name(pid: int) -> str:
    """Image name (e.g. "AppleWin.exe") for a PID, or "" if it can't be read."""
    try:
        handle = win32api.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    except Exception:
        return ""
    try:
        return Path(win32process.GetModuleFileNameEx(handle, 0)).name
    except Exception:
        return ""
    finally:
        win32api.CloseHandle(handle)


def find_window(selector: str) -> int:
    """Resolve `--window` to an HWND. See the module docstring for the rules."""
    if selector.isdigit():
        n = int(selector)
        if win32gui.IsWindow(n):
            return n
        target_pid = n
        matches = []

        def _by_pid(hwnd, _):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid == target_pid:
                    matches.append(hwnd)

        win32gui.EnumWindows(_by_pid, None)
        if not matches:
            raise SystemExit(f"no visible window belongs to PID {target_pid}")
        return matches[0]

    needle = selector.lower()
    matches = []

    def _by_name(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        proc = _process_name(pid)
        if needle in title.lower() or needle in proc.lower():
            matches.append((hwnd, title))

    win32gui.EnumWindows(_by_name, None)
    if not matches:
        raise SystemExit(f"no window matching {selector!r} (checked title and process name)")
    return matches[0][0]


def capture(hwnd: int) -> Image.Image:
    """Screen-coordinate grab of the window's rect -- what `emukeys.ps1` does."""
    rect = win32gui.GetWindowRect(hwnd)
    return ImageGrab.grab(bbox=rect)


def is_foreground(hwnd: int) -> bool:
    return win32gui.GetForegroundWindow() == hwnd


def frames_differ(a: Image.Image, b: Image.Image, threshold: float) -> bool:
    """True if `b` differs from `a` by more than `threshold` mean grayscale delta.

    `threshold <= 0` means any differing pixel at all counts -- the exact
    byte-for-byte check. A small positive threshold (the default) absorbs a
    single blinking cursor or one flickering pixel without ever masking real
    text changing on screen; it does not need to discriminate finely because
    a real screen update moves far more than one pixel's worth of mean delta.
    """
    if a.size != b.size:
        return True
    diff = ImageChops.difference(a.convert("L"), b.convert("L"))
    bbox = diff.getbbox()
    if bbox is None:
        return False
    if threshold <= 0:
        return True
    hist = diff.histogram()
    total = sum(i * n for i, n in enumerate(hist))
    mean = total / (a.width * a.height)
    return mean > threshold


def emit(event: dict) -> None:
    print(json.dumps(event), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--window", default="AppleWin",
        help="HWND, PID, or a substring of the window title/process name (default: AppleWin)",
    )
    parser.add_argument("--interval", type=float, default=0.5, help="seconds between polls (default 0.5)")
    parser.add_argument(
        "--idle-after", type=float, default=3.0,
        help="seconds of no change before one IDLE event fires (default 3.0)",
    )
    parser.add_argument(
        "--threshold", type=float, default=0.5,
        help="mean grayscale delta (0-255) to count as a real change (default 0.5; 0 = any pixel)",
    )
    parser.add_argument("--once", action="store_true", help="capture and OCR a single frame, then exit")
    parser.add_argument("--save-dir", help="also save every changed frame here as a timestamped PNG")
    parser.add_argument(
        "--psm", type=int, default=6,
        help="tesseract --psm mode (default 6, 'uniform block of text' -- tried "
        "against a real AppleWin frame and read the command line and banner "
        "text best of psm 3/4/6/11; still misreads punctuation like parens on "
        "this blocky bitmap font, so treat OCR text as fuzzy, not exact)",
    )
    args = parser.parse_args()

    hwnd = find_window(args.window)
    save_dir = Path(args.save_dir) if args.save_dir else None
    if save_dir:
        save_dir.mkdir(parents=True, exist_ok=True)

    emit({"event": "watch_start", "hwnd": hwnd, "title": win32gui.GetWindowText(hwnd)})

    start = time.monotonic()
    prev: Image.Image | None = None
    last_change = start
    idle_reported = False

    try:
        while True:
            now = time.monotonic()
            frame = capture(hwnd)
            changed = prev is None or frames_differ(prev, frame, args.threshold)

            if changed:
                text = pytesseract.image_to_string(frame, config=f"--psm {args.psm}")
                record = {
                    "event": "change",
                    "t": round(now - start, 2),
                    "foreground": is_foreground(hwnd),
                    "text": text,
                }
                if save_dir:
                    path = save_dir / f"{now - start:07.2f}.png"
                    frame.save(path)
                    record["frame"] = str(path)
                emit(record)
                prev = frame
                last_change = now
                idle_reported = False
            elif not idle_reported and (now - last_change) >= args.idle_after:
                emit({"event": "idle", "t": round(now - start, 2)})
                idle_reported = True

            if args.once:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
