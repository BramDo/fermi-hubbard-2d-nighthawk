$ErrorActionPreference = "Stop"

$RepoWin = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$Drive = $RepoWin.Substring(0, 1).ToLowerInvariant()
$Tail = $RepoWin.Substring(2).Replace([char]92, [char]47)
$RepoWsl = "/mnt/$Drive$Tail"

$RunDir = "results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111"

wsl.exe --cd "$RepoWsl" /home/bram/.venvs/qiskit/bin/python analyze_cuprate_2d_sector_conditioned.py `
  --run-dir "$RunDir" `
  --max-near-distance 2
