$ErrorActionPreference = "Stop"

$RepoWin = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$RepoWinForWsl = $RepoWin -replace "\\", "/"
$RepoWsl = (wsl.exe wslpath -a "$RepoWinForWsl").Trim()
$Python = "/home/bram/.venvs/qiskit/bin/python"
$RunDir = "results_cuprate_2d/validation_ladder_steps1/cuprate_4x4_holes2_steps1"
$MpsDir = "$RunDir/mps_shallow_t_only_steps1"

wsl.exe --cd "$RepoWsl" "$Python" "compare_cuprate_2d_observables.py" `
  --run-dir "$RunDir" `
  --outdir "$RunDir/observable_comparison_shallow_t_only_steps1_vs_mps" `
  --reference-source "mps" `
  --target-step 1 `
  --target-time 0.1 `
  --site-source "mps:mps_chi64:$MpsDir/cuprate_2d_mps_site_observables_chi64.csv" `
  --bond-source "mps:$MpsDir/cuprate_2d_mps_bond_observables_chi64.csv" `
  --tdhf-path "$RunDir/cuprate_2d_tdhf_observables.csv" `
  --gaussian-path "$RunDir/cuprate_2d_gaussian_observables.csv" `
  --ibm-site-path "$RunDir/ibm_hardware_steps1_shallow_t_only_best_layout/cuprate_2d_ibm_site_observables.csv" `
  --ibm-bond-path "$RunDir/ibm_hardware_steps1_shallow_t_only_best_layout/cuprate_2d_ibm_bond_observables.csv" `
  --fire-opal-site-path "$RunDir/fire_opal_shallow_t_only_abstract/cuprate_2d_fire_opal_site_observables.csv" `
  --fire-opal-bond-path "$RunDir/fire_opal_shallow_t_only_abstract/cuprate_2d_fire_opal_bond_observables.csv"
