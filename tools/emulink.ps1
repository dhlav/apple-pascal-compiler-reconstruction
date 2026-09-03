# Link one compiled program against its assembled native half.
#
# PREFER `python tools/emuremote.py link --host X --lib Y --out Z` (findings
# 210-213). The race this script's own note below calls "not fully solved"
# -- prompts answered on a timer, which scrambled an output filename into
# "NK.CODE" more than once -- is solved there by not racing: every answer
# waits for the prompt it answers, which the Linker needs more than the
# other two tools because its prompt sequence depends on the data. It also
# verifies the result by segment dictionary rather than trusting that the
# prompts went by, since a failed link writes an output file anyway. This
# script remains the fallback and is unchanged.
#
# The last step of a reconstruction that has both: the compiler leaves an
# EXTERNAL procedure as a stub, and only SYSTEM.LINKER puts the 6502 in its
# place. Same shape as emucompile.ps1 and emuassemble.ps1 -- boot, type the
# whole command, screenshot, shut the emulator down so the images flush.
#
#   .\tools\emulink.ps1 -Host SKEL13 -Lib LIBRARY -Out SKEL13LNK   # SYSHD -- the default now
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
# The hard-disk layout (the default) uses SYSHD: for everything instead of
# -Vol (one volume now, not SYSHD+WORKHD split across two), and sends the
# prompts as separate SendKeys calls rather than one burst: SYSTEM.LINKER's
# own load off disk is slow enough to eat characters typed right behind the
# bare "L" (finding: HD acceptance session, 2026-08-26 -- the single-burst
# form scrambled into an unrelated filename, "NK.CODE", every time it was
# tried). The output file is created as `NAME.CODE[*]`, not plain
# `NAME.CODE`: a single volume claims all free space for a new file by
# default and only shrinks it back on a clean close, which starved a
# codefile created this way against the Linker's own scratch file when both
# had to share one volume -- the manual's own fix for a one-drive system.
# -Vol applies only with -Floppy. -HardDisk is accepted but redundant now.
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
# one). Only raise it when the caller left -Boot at its default. NOTE: -Boot 6
# still was NOT enough on at least one later run (same "NK.CODE" scramble,
# even though a manual step-by-step run at the same wait times, confirming
# each prompt with a screenshot before sending the next answer, went
# through clean every time) -- this script is racing the boot on a timer
# with no way to confirm the prompt actually arrived, and that race is not
# fully solved. If it scrambles, either raise -Boot further or drive it by
# hand with emukeys.ps1 one prompt at a time, confirming each with -Shot.
if ($UseHD -and -not $PSBoundParameters.ContainsKey("Boot")) { $Boot = 6 }

Get-Process AppleWin -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue
Start-Sleep -Milliseconds 500
if ($UseHD) {
  # An exec file (finding 124), not live SendKeys -- see emucompile.ps1's
  # module note. Tried, and a first test (host = SKEL13) looked like it
  # broke this badly -- but SKEL13 is the plain declaration skeleton
  # with no unresolved EXTERNAL, so it links after the host file alone
  # (this module's own note above already says so); the script's extra
  # scripted answers, meant for prompts that never appear, landed on the
  # Command: menu instead, and "SKEL13LNK" contains an "L" that
  # re-triggered Link with the tail as a bogus host answer -- a test
  # picked wrong, not a bug in exec files or in this script. Re-verified
  # against FORMATTR/FMTNATIV (a host that actually has an unresolved
  # EXTERNAL, finding 104's own pair) before trusting this.
  $HD1 = "$root\build\disks\HD1.hdv"
  $linkKeys = "LSYSHD:$HostFile.CODE{ENTER}SYSHD:$Lib.CODE{ENTER}" +
              "{ENTER}{ENTER}SYSHD:$Out.CODE[*]{ENTER}"
  python "$root\tools\execfile.py" $HD1 GOLINK $linkKeys
  if ($LASTEXITCODE -ne 0) { throw "execfile.py failed to install GOLINK.TEXT" }
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
  # X EXEC/SYSHD:GOLINK -- the exec file installed above already holds
  # every prompt's answer (host, lib, the two blank lines that end the
  # lib list and skip the map file, then the output name), so there is
  # nothing left to answer prompt-by-prompt here (finding 124). Only
  # correct for a host file with a real unresolved EXTERNAL -- see the
  # module note above for what happens with one that has none.
  & "$here\emukeys.ps1" -Keys "XEXEC/SYSHD:GOLINK{ENTER}" -Wait ($Link * 1000) -Shot $Shot -PerKey $PerKey
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
if ($UseHD) { "closed; HD1.hdv (SYSHD) flushed" } else { "closed; $Vol flushed" }
