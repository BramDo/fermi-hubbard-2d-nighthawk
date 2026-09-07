$ErrorActionPreference = "Stop"

$RepoWin = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$RepoWinForWsl = $RepoWin -replace "\\", "/"
$RepoWsl = (wsl.exe wslpath -a "$RepoWinForWsl").Trim()
$Python = "/home/bram/.venvs/qiskit/bin/python"
$Backend = "ibm_marrakesh"
$RunDir = "results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1"
$OutDir = "$RunDir/ibm_hardware_steps1_shallow_t_only_best_layout"

wsl.exe --cd "$RepoWsl" "$Python" "cuprate_2d_ibm_hardware_runner.py" `
  --config "$RunDir/cuprate_2d_config.json" `
  --outdir "$OutDir" `
  --backend "$Backend" `
  --steps 1 `
  --shots 1024 `
  --circuit-family "number_preserving_t_only" `
  --readout-repetitions 3 `
  --readout-shots 4096 `
  --optimization-level 1 `
  --wait-seconds 0 `
  --poll-interval 30 `
  --retrieve
