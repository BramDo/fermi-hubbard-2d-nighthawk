$ErrorActionPreference = "Stop"

$RepoWin = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$RepoWinForWsl = $RepoWin -replace "\\", "/"
$RepoWsl = (wsl.exe wslpath -a "$RepoWinForWsl").Trim()
$Python = "/home/bram/.venvs/qiskit/bin/python"
$RunDir = "results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111"

wsl.exe --cd "$RepoWsl" "$Python" "cuprate_2d_gaussian_baseline.py" `
  --config "$RunDir/cuprate_2d_config.json" `
  --outdir "$RunDir/gaussian_majorana_baseline" `
  --steps 1
