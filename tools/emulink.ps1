# Link one compiled program against its assembled native half.
#
# The last step of a reconstruction that has both: the compiler leaves an
# EXTERNAL procedure as a stub, and only SYSTEM.LINKER puts the 6502 in its
# place. Same shape as emucompile.ps1 and emuassemble.ps1 -- boot, type the
# whole command, screenshot, shut the emulator down so the images flush.
#
#   .\tools\emulink.ps1 -Host FORMATTR -Lib FMTNATIV -Out FORMATTR
#
# Both codefiles have to be on a mounted volume already; this does not put
# them there. The Linker's prompts, in order, are the host file, then the
# library files one at a time until an empty line ends the list, then the map
# file (<ret> for none), then the output file.
param(
  [string]$HostFile = "FORMATTR",
  [string]$Lib = "FMTNATIV",
  [string]$Out = "LINKED",
  [string]$Vol = "WORK2:",
  [int]$Boot = 3,
  [int]$Link = 30,
  [string]$Shot = "",
  [int]$PerKey = 60
)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $here
if ($Shot -eq "") { $Shot = Join-Path $env:TEMP "emulink-$Out.png" }

Get-Process AppleWin -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue
Start-Sleep -Milliseconds 500
Start-Process -FilePath "python" `
  -ArgumentList @("$root\tools\runemu.py","--boot128","--release","1.3","--work2") `
  -WindowStyle Hidden
Start-Sleep -Seconds 2

& "$here\emukeys.ps1" -Wait ($Boot * 1000) | Out-Null

# L(ink, host, lib, <ret> to end the lib list, <ret> for no map, output.
$keys = "L$Vol$HostFile.CODE{ENTER}$Vol$Lib.CODE{ENTER}{ENTER}{ENTER}$Vol$Out.CODE{ENTER}"
& "$here\emukeys.ps1" -Keys $keys -Wait ($Link * 1000) -Shot $Shot -PerKey $PerKey

Get-Process AppleWin -EA SilentlyContinue |
  ForEach-Object { $_.CloseMainWindow() | Out-Null }
Start-Sleep -Milliseconds 2500
Get-Process AppleWin -EA SilentlyContinue | Stop-Process -Force -EA SilentlyContinue
Start-Sleep -Milliseconds 800
"closed; $Vol flushed"
