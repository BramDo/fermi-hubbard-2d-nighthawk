$ErrorActionPreference = "Stop"

$RepoWin = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$Drive = $RepoWin.Substring(0, 1).ToLowerInvariant()
$Tail = $RepoWin.Substring(2).Replace([char]92, [char]47)
$RepoWsl = "/mnt/$Drive$Tail"
$Python = "/home/bram/.venvs/qiskit/bin/python"
$RunDir = "results_cuprate_2d/validation_3x3_steps1/cuprate_3x3_holes1_steps1"
$OutDir = "$RunDir/ibm_hardware_steps1_best_mit"
$Layout = "$RunDir/layout_scout/best_layout.json"
$LayoutWin = Join-Path $RepoWin ($Layout -replace "/", "\")
$BestSeed = (Get-Content -Raw -LiteralPath $LayoutWin | ConvertFrom-Json).recommended_runner_args.seed_transpiler

wsl.exe --cd "$RepoWsl" "$Python" "cuprate_2d_ibm_hardware_runner.py" `
  --config "$RunDir/cuprate_2d_config.json" `
  --outdir "$OutDir" `
  --backend "ibm_marrakesh" `
  --steps 1 `
  --shots 1024 `
  --readout-repetitions 3 `
  --readout-shots 4096 `
  --optimization-level 1 `
  --seed-transpiler "$BestSeed" `
  --wait-seconds 0 `
  --poll-interval 30 `
  --submit
