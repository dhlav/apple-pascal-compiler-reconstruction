# Link one compiled program against its assembled native half.
#
# The last step of a reconstruction that has both: the compiler leaves an
# EXTERNAL procedure as a stub, and only SYSTEM.LINKER puts the 6502 in its
# place. Same shape as emucompile.ps1 and emuassemble.ps1 -- boot, type the
# whole command, screenshot, shut the emulator down so the images flush.
#
#   .\tools\emulink.ps1 -Host SKEL13 -Lib LIBRARY -Out SKEL13LNK   # SYSHD/WORKHD -- the default now
#   .\tools\emulink.ps1 -Host FORMATTR -Lib FMTNATIV -Out FORMATTR -Floppy
#
# Both codefiles have to be on a mounted volume already; this does not put
# them there. The Linker's prompts, in order, are the host file, then the
# library files one at a time until an empty line ends the list, then the map
# file (<ret> for none), then the output file -- though a host file with no
# unresolved EXTERNAL of its own (e.g. the plain declaration skeleton) skips
# straight to "All segments linked" after the host file alone, which is
# correct, not a hang.
#
# The hard-disk layout (the default) uses SYSHD:/WORKHD: instead of -Vol,
# and sends the prompts as separate SendKeys calls rather than one burst:
# SYSTEM.LINKER's own load off disk is slow enough to eat characters typed
# right behind the bare "L" (finding: HD acceptance session, 2026-08-26 --
# the single-burst form scrambled into an unrelated filename, "NK.CODE",
# every time it was tried). -Vol applies only with -Floppy. -HardDisk is
# accepted but redundant now.
param(
  [string]$HostFile = "FORMATTR",
  [string]$Lib = "FMTNATIV",
  [string]$Out = "LINKED",
  [string]$Vol = "WORK2:",
  [switch]$HardDisk,      # accepted for explicitness; this is the default now
  [switch]$Floppy,        # opt back into the four-floppy layout
  [int]$Boot = 3,
  [int]$Link = 30,
  [string]$Shot = "",
  [int]$PerKey = 60
)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
if ($Shot -eq "") { $Shot = Join-Path $env:TEMP "emulink-$Out.png" }
$UseHD = -not $Floppy
# 60ms lost characters even split across calls (see the module note) --
# 100ms didn't, in the same run. Only raise it when the caller left -PerKey
# at its default.
if ($UseHD -and -not $PSBoundParameters.ContainsKey("PerKey")) { $PerKey = 100 }
# The real culprit behind that same run's "NK.CODE": -Boot 3 isn't enough
# for the HD boot to reach Command: before "L" is sent -- the SmartPort boot
# (runemu.py --hd) reliably needed ~7-8s start to finish in manual testing,
# not the ~5.5s (0.5 + 2 + Boot*1000) this script gave it before. "L" landed
# on a screen that wasn't ready yet and was lost; the LAST of the later
# sends was the first to arrive at a live prompt, and its tail is what
# "NK.CODE" actually was (the end of the *output* filename, not the host
# one). Only raise it when the caller left -Boot at its default. NOTE: this
# particular fix has not itself been confirmed by a clean automated run yet
# (the two attempts after it was made lost window focus to something else on
# screen before reaching it) -- the reasoning is solid but treat the first
# real run of it as a check, not a known-good path.
if ($UseHD -and -not $PSBoundParameters.ContainsKey("Boot")) { $Boot = 6 }

Get-Process AppleWin -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue
Start-Sleep -Milliseconds 500
if ($UseHD) {
  Start-Process -FilePath "python" `
    -ArgumentList @("$root\tools\runemu.py","--hd") -WindowStyle Hidden
} else {
  Start-Process -FilePath "python" `
    -ArgumentList @("$root\tools\runemu.py","--floppy","--boot128","--release","1.3","--work2") `
    -WindowStyle Hidden
}
Start-Sleep -Seconds 2

& "$here\emukeys.ps1" -Wait ($Boot * 1000) | Out-Null

if ($UseHD) {
  # L(ink, then each prompt answered separately once it has actually
  # appeared, not on a shared timer -- see the module note.
  & "$here\emukeys.ps1" -Keys "L" -Wait 3000 -PerKey $PerKey | Out-Null
  & "$here\emukeys.ps1" -Keys "WORKHD:$HostFile.CODE{ENTER}" -Wait 2000 -PerKey $PerKey | Out-Null
  & "$here\emukeys.ps1" -Keys "SYSHD:$Lib.CODE{ENTER}" -Wait 2000 -PerKey $PerKey | Out-Null
  & "$here\emukeys.ps1" -Keys "{ENTER}" -Wait 1500 -PerKey $PerKey | Out-Null
  & "$here\emukeys.ps1" -Keys "{ENTER}" -Wait 1500 -PerKey $PerKey | Out-Null
  & "$here\emukeys.ps1" -Keys "WORKHD:$Out.CODE{ENTER}" -Wait ($Link * 1000) -Shot $Shot -PerKey $PerKey
} else {
  # L(ink, host, lib, <ret> to end the lib list, <ret> for no map, output.
  $keys = "L$Vol$HostFile.CODE{ENTER}$Vol$Lib.CODE{ENTER}{ENTER}{ENTER}$Vol$Out.CODE{ENTER}"
  & "$here\emukeys.ps1" -Keys $keys -Wait ($Link * 1000) -Shot $Shot -PerKey $PerKey
}

Get-Process AppleWin -EA SilentlyContinue |
  ForEach-Object { $_.CloseMainWindow() | Out-Null }
Start-Sleep -Milliseconds 2500
Get-Process AppleWin -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue
Start-Sleep -Milliseconds 800
if ($UseHD) { "closed; HD2.hdv (WORKHD) flushed" } else { "closed; $Vol flushed" }
