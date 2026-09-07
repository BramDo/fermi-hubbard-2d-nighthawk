$ErrorActionPreference = "Stop"

$RepoWin = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$RepoWinForWsl = $RepoWin -replace "\\", "/"
$RepoWsl = (wsl.exe wslpath -a "$RepoWinForWsl").Trim()
$Python = "/home/bram/.venvs/qiskit/bin/python"
$RunDir = "results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1"
$MpsDir = "$RunDir/mps_shallow_t_only_steps1"

wsl.exe --cd "$RepoWsl" "$Python" "compare_cuprate_2d_observables.py" `
  --run-dir "$RunDir" `
  --outdir "$RunDir/observable_comparison_shallow_t_only_steps1_vs_mps_qelib_fallback" `
  --reference-source "mps32" `
  --target-step 1 `
  --target-time 0.1 `
  --site-source "mps16:mps_chi16:$MpsDir/cuprate_2d_mps_site_observables_chi16.csv" `
  --site-source "mps32:mps_chi32:$MpsDir/cuprate_2d_mps_site_observables_chi32.csv" `
  --bond-source "mps16:$MpsDir/cuprate_2d_mps_bond_observables_chi16.csv" `
  --bond-source "mps32:$MpsDir/cuprate_2d_mps_bond_observables_chi32.csv" `
  --tdhf-path "$RunDir/cuprate_2d_tdhf_observables.csv" `
  --gaussian-path "$RunDir/cuprate_2d_gaussian_observables.csv" `
  --ibm-site-path "$RunDir/ibm_hardware_steps1_shallow_t_only_best_layout/cuprate_2d_ibm_site_observables.csv" `
  --ibm-bond-path "$RunDir/ibm_hardware_steps1_shallow_t_only_best_layout/cuprate_2d_ibm_bond_observables.csv" `
  --fire-opal-site-path "$RunDir/fire_opal_shallow_t_only_qelib_fallback/cuprate_2d_fire_opal_site_observables.csv" `
  --fire-opal-bond-path "$RunDir/fire_opal_shallow_t_only_qelib_fallback/cuprate_2d_fire_opal_bond_observables.csv"
