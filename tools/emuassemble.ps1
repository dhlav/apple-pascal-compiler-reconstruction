# Assemble one file with Apple's own SYSTEM.ASSMBLER, start to finish.
#
# The acceptance tier for everything in src/native/ (findings 44e, 98e).
# tools/asm6502.py is only the fast tier: it can falsify a source, but the
# assembler that shipped is what decides. This is emucompile.ps1's twin and
# works the same way -- boot, type the whole command at once, screenshot,
# shut the emulator down so AppleWin flushes the disk images.
#
#   .\tools\emuassemble.ps1 -Name SEARCH              # SYSHD -- the default now
#   .\tools\emuassemble.ps1 -Name FMTNATIV -Floppy    # the old four-floppy layout
#
# One thing differs from a compile on the floppy layout, and it is the
# reason for -Prefix. SYSTEM.ASSMBLER opens two files of its own:
# `%6502.ERRORS`, which is found on the volume the assembler itself was
# loaded from, and `6502.OPCODES`, written with no volume at all -- so it is
# looked for on the PREFIX volume, which after a boot is the boot volume.
# BOOT128 does not carry it; APPLE2 does, beside the assembler. So the
# Filer's P(refix is set to APPLE2: first, and every file named after that
# is named with its volume.
#
# The hard-disk layout (the default) needs none of that: SYSHD carries
# 6502.OPCODES itself, and the boot volume already *is* SYSHD, so the
# default P(refix resolves without help. -Prefix and -NoPrefix apply only
# with -Floppy. -HardDisk is accepted but redundant now.
#
# The codefile is created as `NAME.CODE[*]`, not plain `NAME.CODE`, on the
# hard-disk layout: a single Pascal volume claims *all* free space for a new
# file by default and only shrinks it back on a clean close, so this and
# SYSTEM.ASSMBLER's own `%LINKER.INFO` scratch file (also on SYSHD now)
# raced for it and the codefile got "I/O error: no room on volume" with
# thousands of blocks free (finding: HD acceptance session, 2026-08-26). Not
# a bug in this tooling -- the manual's own fix for a one-drive system (ch.
# 3/5) is exactly this size specifier.
param(
  [string]$Name = "FMTNATIV",
  [int]$Boot = 3,           # seconds to let the system boot before typing
  [int]$Assemble = 25,      # seconds to let the assembly run
  [string]$Shot = "",
  [string]$Prefix = "APPLE2:",
  [switch]$NoPrefix,        # skip the Filer step, to see it fail (-Floppy only)
  [switch]$HardDisk,        # accepted for explicitness; this is the default now
  [switch]$Floppy,          # opt back into the four-floppy layout
  [int]$PerKey = 60         # ms between characters; raise it if keys are lost
)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
if ($Shot -eq "") { $Shot = Join-Path $env:TEMP "emuassemble-$Name.png" }
$UseHD = -not $Floppy

Get-Process AppleWin -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue
Start-Sleep -Milliseconds 500
if ($UseHD) {
  # An exec file (finding 124), not live SendKeys -- see emucompile.ps1's
  # module note. This is the path that most needed it: the module note
  # above documents SYSTEM.ASSMBLER's own load eating characters typed
  # right behind a live "A", which an exec file cannot suffer from at all.
  $HD1 = "$root\build\disks\HD1.hdv"
  $asmKeys = "ASYSHD:$Name.TEXT{ENTER}SYSHD:$Name.CODE[*]{ENTER}{ENTER}"
  python "$root\tools\execfile.py" $HD1 GOASM $asmKeys
  if ($LASTEXITCODE -ne 0) { throw "execfile.py failed to install GOASM.TEXT" }
  Start-Process -FilePath "python" `
    -ArgumentList @("$root\tools\runemu.py","--hd") -WindowStyle Hidden
} else {
  # --work2 keeps the codefile off WORK:, which the source already fills.
  Start-Process -FilePath "python" `
    -ArgumentList @("$root\tools\runemu.py","--floppy","--boot128","--release","1.3","--work2") `
    -WindowStyle Hidden
}
Start-Sleep -Seconds 2

& "$here\emukeys.ps1" -Wait ($Boot * 1000) | Out-Null

if (-not $UseHD -and -not $NoPrefix) {
  # F(iler, P(refix, the volume, Q(uit.
  & "$here\emukeys.ps1" -Keys "FP$Prefix{ENTER}Q" -Wait 4000 -PerKey $PerKey |
    Out-Null
}

# A(ssemble, the source file, the codefile, then <ret> for no listing.
#
# On the HD path this is now X EXEC/SYSHD:GOASM -- the exec file installed
# above already holds the whole A...{ENTER}...{ENTER}...{ENTER} sequence,
# so there is nothing left to split across SendKeys calls or race against
# SYSTEM.ASSMBLER's own slow load (finding 124). The floppy path is
# unchanged: still the single live-SendKeys burst that was already
# verified working there.
if ($UseHD) {
  $keys = "XEXEC/SYSHD:GOASM{ENTER}"
} else {
  $keys = "AWORK:$Name.TEXT{ENTER}WORK2:$Name.CODE{ENTER}{ENTER}"
}
& "$here\emukeys.ps1" -Keys $keys -Wait ($Assemble * 1000) -Shot $Shot -PerKey $PerKey

Get-Process AppleWin -EA SilentlyContinue |
  ForEach-Object { $_.CloseMainWindow() | Out-Null }
Start-Sleep -Milliseconds 2500
Get-Process AppleWin -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue
Start-Sleep -Milliseconds 800
if ($UseHD) { "closed; HD1.hdv (SYSHD) flushed" } else { "closed; WORK2.dsk flushed" }
