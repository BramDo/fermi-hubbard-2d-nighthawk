$ErrorActionPreference = "Stop"

$RepoWin = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$Drive = $RepoWin.Substring(0, 1).ToLowerInvariant()
$Tail = $RepoWin.Substring(2).Replace([char]92, [char]47)
$RepoWsl = "/mnt/$Drive$Tail"
$Python = "/home/bram/.venvs/qiskit/bin/python"
$RunDir = "results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1"

wsl.exe --cd "$RepoWsl" "$Python" "compare_cuprate_2d_observables.py" `
  --run-dir "$RunDir" `
  --outdir "$RunDir/observable_comparison_shallow_sector_vs_exact_full" `
  --reference-source "exact_full" `
  --site-source "exact_full:fixed_sector:$RunDir/exact_sector_full_hubbard/cuprate_2d_exact_site_observables.csv" `
  --site-source "exact_t_only:fixed_sector:$RunDir/exact_sector_t_only_hubbard/cuprate_2d_exact_site_observables.csv" `
  --normalized-site-path "$RunDir/sector_conditioned_shallow_t_only/sector_conditioned_site_observables.csv"
