$ErrorActionPreference = "Stop"

$RepoWin = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$Drive = $RepoWin.Substring(0, 1).ToLowerInvariant()
$Tail = $RepoWin.Substring(2).Replace([char]92, [char]47)
$RepoWsl = "/mnt/$Drive$Tail"
$Python = "/home/bram/.venvs/qiskit/bin/python"
$RunDir = "results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1"
$OutDir = "$RunDir/time_sweep_steps4"

wsl.exe --cd "$RepoWsl" "$Python" "cuprate_2d_exact_sector_baseline.py" `
  --config "$RunDir/cuprate_2d_config.json" `
  --outdir "$OutDir/exact_sector_full_hubbard" `
  --model "full_hubbard" `
  --steps 4

wsl.exe --cd "$RepoWsl" "$Python" "cuprate_2d_exact_sector_baseline.py" `
  --config "$RunDir/cuprate_2d_config.json" `
  --outdir "$OutDir/exact_sector_t_only_hubbard" `
  --model "t_only_hubbard" `
  --steps 4

wsl.exe --cd "$RepoWsl" "$Python" "cuprate_2d_tdhf_simulation.py" `
  --config "$RunDir/cuprate_2d_config.json" `
  --outdir "$OutDir/tdhf_simulation" `
  --steps 4 `
  --internal-dt 0.005

wsl.exe --cd "$RepoWsl" "$Python" "cuprate_2d_gaussian_baseline.py" `
  --config "$RunDir/cuprate_2d_config.json" `
  --outdir "$OutDir/gaussian_majorana_baseline" `
  --steps 4

wsl.exe --cd "$RepoWsl" "$Python" "compare_cuprate_2d_time_sweep.py" `
  --outdir "$OutDir/observable_time_sweep" `
  --reference-source "exact_full" `
  --site-source "exact_full:fixed_sector:$OutDir/exact_sector_full_hubbard/cuprate_2d_exact_site_observables.csv" `
  --site-source "exact_t_only:fixed_sector:$OutDir/exact_sector_t_only_hubbard/cuprate_2d_exact_site_observables.csv" `
  --site-source "tdhf:mean_field:$OutDir/tdhf_simulation/cuprate_2d_tdhf_observables.csv" `
  --site-source "gaussian_u0:free_fermion:$OutDir/gaussian_majorana_baseline/cuprate_2d_gaussian_observables.csv"
