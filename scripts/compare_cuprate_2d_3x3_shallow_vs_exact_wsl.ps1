$ErrorActionPreference = "Stop"

$RepoWin = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$Drive = $RepoWin.Substring(0, 1).ToLowerInvariant()
$Tail = $RepoWin.Substring(2).Replace([char]92, [char]47)
$RepoWsl = "/mnt/$Drive$Tail"
$Python = "/home/bram/.venvs/qiskit/bin/python"
$RunDir = "results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1"

wsl.exe --cd "$RepoWsl" "$Python" "compare_cuprate_2d_observables.py" `
  --run-dir "$RunDir" `
  --outdir "$RunDir/observable_comparison_shallow_vs_exact_full" `
  --reference-source "exact_full" `
  --tdhf-path "$RunDir/cuprate_2d_tdhf_observables.csv" `
  --gaussian-path "$RunDir/cuprate_2d_gaussian_observables.csv" `
  --site-source "exact_full:fixed_sector:$RunDir/exact_sector_full_hubbard/cuprate_2d_exact_site_observables.csv" `
  --site-source "exact_t_only:fixed_sector:$RunDir/exact_sector_t_only_hubbard/cuprate_2d_exact_site_observables.csv" `
  --bond-source "exact_full:$RunDir/exact_sector_full_hubbard/cuprate_2d_exact_bond_observables.csv" `
  --bond-source "exact_t_only:$RunDir/exact_sector_t_only_hubbard/cuprate_2d_exact_bond_observables.csv" `
  --ibm-site-path "$RunDir/ibm_hardware_steps1_shallow_t_only/cuprate_2d_ibm_site_observables.csv" `
  --ibm-bond-path "$RunDir/ibm_hardware_steps1_shallow_t_only/cuprate_2d_ibm_bond_observables.csv" `
  --fire-opal-site-path "$RunDir/fire_opal_shallow_t_only_qelib/cuprate_2d_fire_opal_site_observables.csv" `
  --fire-opal-bond-path "$RunDir/fire_opal_shallow_t_only_qelib/cuprate_2d_fire_opal_bond_observables.csv"
