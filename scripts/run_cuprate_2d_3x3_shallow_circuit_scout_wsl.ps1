$ErrorActionPreference = "Stop"

$RepoWin = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$Drive = $RepoWin.Substring(0, 1).ToLowerInvariant()
$Tail = $RepoWin.Substring(2).Replace([char]92, [char]47)
$RepoWsl = "/mnt/$Drive$Tail"
$Python = "/home/bram/.venvs/qiskit/bin/python"
$RunDir = "results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1"

wsl.exe --cd "$RepoWsl" "$Python" "cuprate_2d_shallow_circuit_scout.py" `
  --config "$RunDir/cuprate_2d_config.json" `
  --outdir "$RunDir/shallow_circuit_scout" `
  --tdhf-path "$RunDir/cuprate_2d_tdhf_observables.csv" `
  --gaussian-path "$RunDir/cuprate_2d_gaussian_observables.csv" `
  --backend "ibm_marrakesh" `
  --optimization-level 1 `
  --seed-start 1 `
  --seed-count 10
