$ErrorActionPreference = "Stop"

$RepoWin = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$Drive = $RepoWin.Substring(0, 1).ToLowerInvariant()
$Tail = $RepoWin.Substring(2).Replace([char]92, [char]47)
$RepoWsl = "/mnt/$Drive$Tail"
$Python = "/home/bram/.venvs/qiskit/bin/python"
$RunDir = "results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1"

wsl.exe --cd "$RepoWsl" "$Python" "analyze_cuprate_2d_sector_conditioned.py" `
  --run-dir "$RunDir" `
  --config "$RunDir/cuprate_2d_config.json" `
  --outdir "$RunDir/sector_conditioned_qctrl_best_mit" `
  --tdhf-path "$RunDir/cuprate_2d_tdhf_observables.csv" `
  --gaussian-path "$RunDir/cuprate_2d_gaussian_observables.csv" `
  --ibm-raw-path "$RunDir/ibm_hardware_steps1_best_mit/cuprate_2d_ibm_raw_results.json" `
  --fire-opal-raw-path "$RunDir/fire_opal_qctrl_steps1/fire_opal_raw_results.json" `
  --max-near-distance 2
