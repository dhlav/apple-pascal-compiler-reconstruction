# Compile one file with Apple's own compiler, start to finish.
#
# Launches AppleWin on the 128K boot disk, drives C(ompile, waits for it,
# captures the screen and shuts the emulator down again -- which is what
# flushes WORK.dsk, since AppleWin holds the image open until it exits.
#
#   .\tools\emucompile.ps1 -Name SKEL13                  # SYSHD/WORKHD -- the default now
#   .\tools\emucompile.ps1 -Name BODY13 -Compile 40      # a longer source
#   .\tools\emucompile.ps1 -Name BODY11 -Release 1.1 -Floppy   # 1.1's own compiler
#
# The hard-disk layout (SYSHD/WORKHD on the slot-5 HDC, runemu.py --hd,
# mkharddisks.py) is the default: the source must already be on WORKHD
# (mkharddisks.py's own FILES list, or added by hand with cp2), and the
# compiler runs off SYSHD -- there is only one release of the tools on that
# path, 1.3's. -HardDisk is accepted but redundant now; pass -Floppy for the
# older four-floppy layout, where -Release and -Work2 apply.
#
# -Release picks which APPLE2 goes in drive 2 on the floppy layout, and that
# is the only thing that decides which compiler runs there: the boot volume
# is BOOT128 either way -- APPLE1 with the 128K system substituted in -- and
# it carries no SYSTEM.COMPILER of its own. 1.1's compiler is the authority
# for 1.1's p-code, so a 1.1 run must not be left on the default.
#
# The keystrokes all go in one SendKeys call. Apple Pascal has a type-ahead
# buffer and the emulator is running at maximum speed, so there is no need
# to wait for each prompt to appear and then answer it -- three seconds for
# the boot, then the whole command at once, and the system consumes it as
# it gets to each prompt.
param(
  [string]$Name = "BODY13",
  [int]$Boot = 3,          # seconds to let the system boot before typing
  [int]$Compile = 25,      # seconds to let the compile run
  [string]$Shot = "",
  [ValidateSet("1.1", "1.3")]
  [string]$Release = "1.3",   # which APPLE2 -- which compiler -- is in D2 (-Floppy only)
  [switch]$Work2,         # put the codefile on WORK2: (S5D2), not WORK: (-Floppy only)
  [switch]$HardDisk,      # accepted for explicitness; this is the default now
  [switch]$Floppy,        # opt back into the four-floppy layout
  [int]$PerKey = 60       # ms between characters; raise it if keys are lost
)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
if ($Shot -eq "") { $Shot = Join-Path $env:TEMP "emucompile-$Name.png" }
$UseHD = -not $Floppy

Get-Process AppleWin -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue
Start-Sleep -Milliseconds 500
if ($UseHD) {
  $emuargs = @("$root\tools\runemu.py","--hd")
} else {
  $emuargs = @("$root\tools\runemu.py","--floppy","--boot128","--release",$Release)
  if ($Work2) { $emuargs += "--work2" }
}
Start-Process -FilePath "python" -ArgumentList $emuargs -WindowStyle Hidden
Start-Sleep -Seconds 2

# C(ompile, the source file, the codefile, then <ret> for no listing.
if ($UseHD) {
  $keys = "CWORKHD:$Name.TEXT{ENTER}WORKHD:$Name.CODE{ENTER}{ENTER}"
} else {
  $out = if ($Work2) { "WORK2:" } else { "WORK:" }
  $keys = "CWORK:$Name.TEXT{ENTER}$out$Name.CODE{ENTER}{ENTER}"
}
& "$here\emukeys.ps1" -Wait ($Boot * 1000) | Out-Null
& "$here\emukeys.ps1" -Keys $keys -Wait ($Compile * 1000) -Shot $Shot -PerKey $PerKey

Get-Process AppleWin -EA SilentlyContinue |
  ForEach-Object { $_.CloseMainWindow() | Out-Null }
Start-Sleep -Milliseconds 2500
Get-Process AppleWin -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue
Start-Sleep -Milliseconds 800
if ($UseHD) { "closed; HD2.hdv (WORKHD) flushed" } else { "closed; WORK.dsk flushed" }
