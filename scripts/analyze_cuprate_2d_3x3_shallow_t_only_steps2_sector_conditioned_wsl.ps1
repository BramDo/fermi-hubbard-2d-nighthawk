$ErrorActionPreference = "Stop"

$RepoWin = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$Drive = $RepoWin.Substring(0, 1).ToLowerInvariant()
$Tail = $RepoWin.Substring(2).Replace([char]92, [char]47)
$RepoWsl = "/mnt/$Drive$Tail"
$Python = "/home/bram/.venvs/qiskit/bin/python"
$RunDir = "results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1"
$SweepDir = "$RunDir/time_sweep_steps4"

wsl.exe --cd "$RepoWsl" "$Python" "analyze_cuprate_2d_sector_conditioned.py" `
  --run-dir "$RunDir" `
  --config "$RunDir/cuprate_2d_config.json" `
  --outdir "$RunDir/sector_conditioned_shallow_t_only_steps2" `
  --target-step 2 `
  --reference-source "exact_full" `
  --reference-path "$SweepDir/exact_sector_full_hubbard/cuprate_2d_exact_site_observables.csv" `
  --tdhf-path "$SweepDir/tdhf_simulation/cuprate_2d_tdhf_observables.csv" `
  --gaussian-path "$SweepDir/gaussian_majorana_baseline/cuprate_2d_gaussian_observables.csv" `
  --ibm-raw-path "$RunDir/ibm_hardware_steps2_shallow_t_only/cuprate_2d_ibm_raw_results.json" `
  --fire-opal-raw-path "$RunDir/fire_opal_shallow_t_only_steps2_qelib/fire_opal_raw_results.json" `
  --max-near-distance 2
