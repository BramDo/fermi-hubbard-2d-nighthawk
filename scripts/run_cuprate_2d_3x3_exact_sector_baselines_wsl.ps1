$ErrorActionPreference = "Stop"

$RepoWin = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$Drive = $RepoWin.Substring(0, 1).ToLowerInvariant()
$Tail = $RepoWin.Substring(2).Replace([char]92, [char]47)
$RepoWsl = "/mnt/$Drive$Tail"
$Python = "/home/bram/.venvs/qiskit/bin/python"
$RunDir = "results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1"

wsl.exe --cd "$RepoWsl" "$Python" "cuprate_2d_exact_sector_baseline.py" `
  --config "$RunDir/cuprate_2d_config.json" `
  --outdir "$RunDir/exact_sector_full_hubbard" `
  --model "full_hubbard" `
  --steps 1

wsl.exe --cd "$RepoWsl" "$Python" "cuprate_2d_exact_sector_baseline.py" `
  --config "$RunDir/cuprate_2d_config.json" `
  --outdir "$RunDir/exact_sector_t_only_hubbard" `
  --model "t_only_hubbard" `
  --steps 1
