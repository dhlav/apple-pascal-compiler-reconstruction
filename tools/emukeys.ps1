# Drive AppleWin by keystroke and read the screen back.
#
# AppleWin's command line can mount disks and boot but has no switch that
# injects keys, and -screenshot-and-exit is documented for -load-state, so it
# fires before a cold boot finishes. This closes the gap the only way left:
# SendKeys into the window, then capture the window and look at it.
#
#   .\tools\emukeys.ps1 -Keys "F" -Wait 1500 -Shot out.png
#
# Keys uses SendKeys syntax: {ENTER} {ESC} {BS} for the special ones, and
# ^x for control-x. A bare string is typed literally -- except that
# SendKeys itself treats % + ~ ( ) { } as modifier/grouping syntax, not
# literal characters (finding: exec-file session, 2026-08-28 -- an exec
# file's own terminator is `%` by default, and typing a bare "%%" here
# silently sent nothing at all: two ALT-with-no-key events, not two percent
# signs, so the emulator never saw a terminator and the file was left
# stale). Those seven characters are auto-escaped to {%} {+} {~} {(} {)}
# {{} {}} below so a bare string really is typed literally; write an
# explicit {%} etc. yourself only if you want to see the escaping fail
# loudly instead of silently. ^x for control-x is untouched -- that one is
# the documented, intentional exception.

param(
  [string]$Keys = "",
  [int]$Wait = 1500,
  [string]$Shot = "",
  [int]$Settle = 400,
  [int]$PerKey = 60
)
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing, System.Windows.Forms
Add-Type @"
using System; using System.Runtime.InteropServices;
public class EmuWin {
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr h);
  [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, IntPtr pid);
  [DllImport("user32.dll")] public static extern bool AttachThreadInput(uint from, uint to, bool attach);
  [DllImport("user32.dll")] public static extern bool BringWindowToTop(IntPtr h);
  [DllImport("kernel32.dll")] public static extern uint GetCurrentThreadId();
  public struct RECT { public int L, T, R, B; }
}
"@

$p = Get-Process AppleWin -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $p) { throw "AppleWin is not running (python tools/runemu.py)" }
$h = $p.MainWindowHandle
if ([EmuWin]::IsIconic($h)) { [EmuWin]::ShowWindow($h, 9) | Out-Null }
# Windows refuses foreground activation to a process that does not own the
# current foreground window, and it fails silently. Retrying alone is not
# enough: when the operator has left a browser (or anything else) focused
# and never touches this shell, the refusal is permanent and every retry
# loses identically -- that is exactly how a long unattended run dies. The
# documented way through is to attach this thread's input queue to the
# foreground window's thread first, which makes the two threads share a
# foreground state and lets the activation be granted. Attach, activate,
# detach; then verify. The verification below is the safety property and is
# untouched -- this only makes the activation itself actually succeed.
function Set-EmuForeground($hwnd) {
  $me = [EmuWin]::GetCurrentThreadId()
  $fg = [EmuWin]::GetForegroundWindow()
  $other = if ($fg -ne [IntPtr]::Zero) {
    [EmuWin]::GetWindowThreadProcessId($fg, [IntPtr]::Zero)
  } else { 0 }
  $attached = $false
  if ($other -ne 0 -and $other -ne $me) {
    $attached = [EmuWin]::AttachThreadInput($me, $other, $true)
  }
  try {
    [EmuWin]::BringWindowToTop($hwnd) | Out-Null
    [EmuWin]::SetForegroundWindow($hwnd) | Out-Null
  } finally {
    if ($attached) { [EmuWin]::AttachThreadInput($me, $other, $false) | Out-Null }
  }
}
for ($i = 0; $i -lt 12; $i++) {
  Set-EmuForeground $h
  Start-Sleep -Milliseconds ([Math]::Max(150, $Settle / 4))
  if ([EmuWin]::GetForegroundWindow() -eq $h) { break }
}
Start-Sleep -Milliseconds $Settle

# SendKeys types into whatever holds focus, not into a window of our
# choosing. Once, a window activation lost the race and half a filename went
# into the user's terminal instead of the emulator. So: never type without
# confirming AppleWin is foreground, and confirm again afterwards -- if focus
# moved mid-send, say which characters went astray rather than continuing as
# though the emulator received them.
function Assert-Focus($when) {
  if ([EmuWin]::GetForegroundWindow() -ne $h) {
    throw "AppleWin does not have focus $when -- refusing to send keys. " +
          "Nothing was typed into it; do not assume the emulator advanced."
  }
}

if ($Keys -ne "") {
  Assert-Focus "before sending"
  # One character at a time, with a gap. Apple Pascal's type-ahead buffer is
  # filled by *polling* the Apple's keyboard latch, which holds one byte --
  # so a whole command sent in one SendWait outruns the poll and characters
  # are silently dropped. That is not a hypothetical: it turned
  # "CWORK:BODY13.TEXT" into some other command (both E and X are commands
  # at that prompt) and cost a work disk. The gap only has to beat the poll,
  # not the prompts: type-ahead means there is no need to wait for each
  # prompt to appear before answering it.
  $literalEscapes = @{ '%' = '{%}'; '+' = '{+}'; '~' = '{~}';
                        '(' = '{(}'; ')' = '{)}'; '{' = '{{}'; '}' = '{}}' }
  foreach ($tok in [regex]::Matches($Keys, '\{[^}]+\}|.')) {
    $send = $tok.Value
    if ($send.Length -eq 1 -and $literalEscapes.ContainsKey($send)) {
      $send = $literalEscapes[$send]
    }
    [System.Windows.Forms.SendKeys]::SendWait($send)
    Start-Sleep -Milliseconds $PerKey
  }
  Start-Sleep -Milliseconds 150
  # No re-raise here, on purpose. Losing the foreground *during* a send means
  # characters went somewhere else, and raising the window afterwards does
  # not get them back -- the run is already wrong and has to say so.
  if ([EmuWin]::GetForegroundWindow() -ne $h) {
    throw "focus left AppleWin during the send of '$Keys' -- some or all of " +
          "it went to another window. Re-read the screen before continuing."
  }
}
Start-Sleep -Milliseconds $Wait

if ($Shot -ne "") {
  # CopyFromScreen grabs screen pixels at the window's coordinates, not the
  # window's own content. If anything is on top of AppleWin -- an editor, a
  # dialog -- the "screenshot of the emulator" is a photograph of that
  # instead, and it looks plausible enough to act on. Refuse.
  #
  # A long -Wait is ample time for something else to take the foreground (a
  # browser finishing a load, a notification), and an unattended run that has
  # already done the work should not be thrown away over that. Raise the
  # window again first, the same way the send path does. Nothing is typed
  # here, so re-raising costs nothing -- and the refusal below still stands
  # if it does not take.
  for ($i = 0; $i -lt 8; $i++) {
    if ([EmuWin]::GetForegroundWindow() -eq $h) { break }
    Set-EmuForeground $h
    Start-Sleep -Milliseconds 250
  }
  if ([EmuWin]::GetForegroundWindow() -ne $h) {
    throw "AppleWin is not the foreground window at capture time; the " +
          "screenshot would show whatever is on top of it. Not captured."
  }
  $dir = Split-Path -Parent $Shot
  if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force $dir | Out-Null }
  $r = New-Object EmuWin+RECT
  [EmuWin]::GetWindowRect($h, [ref]$r) | Out-Null
  $w = $r.R - $r.L; $ht = $r.B - $r.T
  $bmp = New-Object System.Drawing.Bitmap $w, $ht
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.CopyFromScreen($r.L, $r.T, 0, 0, (New-Object System.Drawing.Size($w, $ht)))
  $bmp.Save($Shot, [System.Drawing.Imaging.ImageFormat]::Png)
  $g.Dispose(); $bmp.Dispose()
  "captured $Shot (${w}x${ht})"
}
