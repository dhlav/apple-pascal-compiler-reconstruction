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
# ^x for control-x. A bare string is typed literally. Omit -Keys to capture
# without typing anything.
param(
  [string]$Keys = "",
  [int]$Wait = 1500,
  [string]$Shot = "",
  [int]$Settle = 400
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
  public struct RECT { public int L, T, R, B; }
}
"@

$p = Get-Process AppleWin -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $p) { throw "AppleWin is not running (python tools/runemu.py)" }
$h = $p.MainWindowHandle
if ([EmuWin]::IsIconic($h)) { [EmuWin]::ShowWindow($h, 9) | Out-Null }
# Windows refuses foreground activation to a process that does not own the
# current foreground window, and it fails silently. Retry rather than give
# up: the usual cause is the operator having just clicked elsewhere.
for ($i = 0; $i -lt 12; $i++) {
  [EmuWin]::SetForegroundWindow($h) | Out-Null
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
  [System.Windows.Forms.SendKeys]::SendWait($Keys)
  Start-Sleep -Milliseconds 150
  if ([EmuWin]::GetForegroundWindow() -ne $h) {
    throw "focus left AppleWin during the send of '$Keys' -- some or all of " +
          "it went to another window. Re-read the screen before continuing."
  }
}
Start-Sleep -Milliseconds $Wait

if ($Shot -ne "") {
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
