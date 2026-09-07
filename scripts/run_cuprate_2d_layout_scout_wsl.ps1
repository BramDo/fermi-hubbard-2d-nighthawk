$ErrorActionPreference = "Stop"

$RepoWin = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$RepoWinForWsl = $RepoWin -replace "\\", "/"
$RepoWsl = (wsl.exe wslpath -a "$RepoWinForWsl").Trim()
$Python = "/home/bram/.venvs/qiskit/bin/python"
$RunDir = "results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111"
$OutDir = "$RunDir/layout_scout"

wsl.exe --cd "$RepoWsl" "$Python" "cuprate_2d_layout_scout.py" `
  --config "$RunDir/cuprate_2d_config.json" `
  --outdir "$OutDir" `
  --backend "ibm_marrakesh" `
  --steps 1 `
  --optimization-level 1 `
  --seed-start 1 `
  --seed-count 50
