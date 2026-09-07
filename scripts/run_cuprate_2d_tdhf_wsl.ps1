$ErrorActionPreference = "Stop"

$RepoWin = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$RepoWinForWsl = $RepoWin -replace "\\", "/"
$RepoWsl = (wsl.exe wslpath -a "$RepoWinForWsl").Trim()
$Python = "/home/bram/.venvs/qiskit/bin/python"
$RunDir = "results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111"

wsl.exe --cd "$RepoWsl" "$Python" "cuprate_2d_tdhf_simulation.py" `
  --config "$RunDir/cuprate_2d_config.json" `
  --outdir "$RunDir/tdhf_simulation" `
  --internal-dt 0.005
