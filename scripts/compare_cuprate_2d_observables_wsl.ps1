$ErrorActionPreference = "Stop"

$RepoWin = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$RepoWinForWsl = $RepoWin -replace "\\", "/"
$RepoWsl = (wsl.exe wslpath -a "$RepoWinForWsl").Trim()
$Python = "/home/bram/.venvs/qiskit/bin/python"
$RunDir = "results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111"

wsl.exe --cd "$RepoWsl" "$Python" "compare_cuprate_2d_observables.py" `
  --run-dir "$RunDir" `
  --outdir "$RunDir/observable_comparison" `
  --reference-source "tdhf"
