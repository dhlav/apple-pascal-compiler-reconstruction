# Assemble one file with Apple's own SYSTEM.ASSMBLER, start to finish.
#
# The acceptance tier for everything in src/native/ (findings 44e, 98e).
# tools/asm6502.py is only the fast tier: it can falsify a source, but the
# assembler that shipped is what decides. This is emucompile.ps1's twin and
# works the same way -- boot, type the whole command at once, screenshot,
# shut the emulator down so AppleWin flushes the disk images.
#
#   .\tools\emuassemble.ps1 -Name FMTNATIV
#
# One thing differs from a compile, and it is the reason for -Prefix.
# SYSTEM.ASSMBLER opens two files of its own: `%6502.ERRORS`, which is found
# on the volume the assembler itself was loaded from, and `6502.OPCODES`,
# written with no volume at all -- so it is looked for on the PREFIX volume,
# which after a boot is the boot volume. BOOT128 does not carry it; APPLE2
# does, beside the assembler. So the Filer's P(refix is set to APPLE2:
# first, and every file named after that is named with its volume.
param(
  [string]$Name = "FMTNATIV",
  [int]$Boot = 3,           # seconds to let the system boot before typing
  [int]$Assemble = 25,      # seconds to let the assembly run
  [string]$Shot = "",
  [string]$Prefix = "APPLE2:",
  [switch]$NoPrefix,        # skip the Filer step, to see it fail
  [int]$PerKey = 60         # ms between characters; raise it if keys are lost
)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
if ($Shot -eq "") { $Shot = Join-Path $env:TEMP "emuassemble-$Name.png" }

Get-Process AppleWin -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue
Start-Sleep -Milliseconds 500
# --work2 keeps the codefile off WORK:, which the source already fills.
Start-Process -FilePath "python" `
  -ArgumentList @("$root\tools\runemu.py","--boot128","--release","1.3","--work2") `
  -WindowStyle Hidden
Start-Sleep -Seconds 2

& "$here\emukeys.ps1" -Wait ($Boot * 1000) | Out-Null

if (-not $NoPrefix) {
  # F(iler, P(refix, the volume, Q(uit.
  & "$here\emukeys.ps1" -Keys "FP$Prefix{ENTER}Q" -Wait 4000 -PerKey $PerKey |
    Out-Null
}

# A(ssemble, the source file, the codefile, then <ret> for no listing.
$keys = "AWORK:$Name.TEXT{ENTER}WORK2:$Name.CODE{ENTER}{ENTER}"
& "$here\emukeys.ps1" -Keys $keys -Wait ($Assemble * 1000) -Shot $Shot -PerKey $PerKey

Get-Process AppleWin -EA SilentlyContinue |
  ForEach-Object { $_.CloseMainWindow() | Out-Null }
Start-Sleep -Milliseconds 2500
Get-Process AppleWin -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue
Start-Sleep -Milliseconds 800
"closed; WORK2.dsk flushed"
