$ErrorActionPreference = "Stop"

$RepoWin = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$RepoWinForWsl = $RepoWin -replace "\\", "/"
$RepoWsl = (wsl.exe wslpath -a "$RepoWinForWsl").Trim()
$Python = "/home/bram/.venvs/qiskit/bin/python"
$RunDir = "results_cuprate_2d/validation_ladder_steps1/cuprate_4x4_holes2_steps1"
$OutDir = "$RunDir/layout_scout_shallow_t_only"

wsl.exe --cd "$RepoWsl" "$Python" "cuprate_2d_layout_scout.py" `
  --config "$RunDir/cuprate_2d_config.json" `
  --outdir "$OutDir" `
  --backend "ibm_marrakesh" `
  --steps 1 `
  --circuit-family "number_preserving_t_only" `
  --optimization-level 1 `
  --seed-start 1 `
  --seed-count 50
