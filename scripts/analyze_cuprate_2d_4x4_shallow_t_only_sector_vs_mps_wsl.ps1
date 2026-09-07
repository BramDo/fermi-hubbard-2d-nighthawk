$ErrorActionPreference = "Stop"

$RepoWin = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$RepoWinForWsl = $RepoWin -replace "\\", "/"
$RepoWsl = (wsl.exe wslpath -a "$RepoWinForWsl").Trim()
$Python = "/home/bram/.venvs/qiskit/bin/python"
$RunDir = "results_cuprate_2d/validation_ladder_steps1/cuprate_4x4_holes2_steps1"
$MpsDir = "$RunDir/mps_shallow_t_only_steps1"

wsl.exe --cd "$RepoWsl" "$Python" "analyze_cuprate_2d_sector_conditioned.py" `
  --run-dir "$RunDir" `
  --config "$RunDir/cuprate_2d_config.json" `
  --outdir "$RunDir/sector_conditioned_shallow_t_only_steps1_vs_mps" `
  --reference-source "mps" `
  --reference-path "$MpsDir/cuprate_2d_mps_site_observables_chi64.csv" `
  --target-step 1 `
  --ibm-raw-path "$RunDir/ibm_hardware_steps1_shallow_t_only_best_layout/cuprate_2d_ibm_raw_results.json" `
  --fire-opal-raw-path "$RunDir/fire_opal_shallow_t_only_abstract/fire_opal_raw_results.json" `
  --max-near-distance 2
