$ErrorActionPreference = "Stop"

$RepoWin = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$RepoWinForWsl = $RepoWin -replace "\\", "/"
$RepoWsl = (wsl.exe wslpath -a "$RepoWinForWsl").Trim()
$Python = "/home/bram/.venvs/qiskit/bin/python"
$RunDir = "results_cuprate_2d/validation_ladder_steps1/cuprate_4x4_holes2_steps1"
$OutDir = "$RunDir/ibm_hardware_steps1_shallow_t_only_best_layout"
$Layout = "$RunDir/layout_scout_shallow_t_only/best_layout.json"
$LayoutWin = Join-Path $RepoWin ($Layout -replace "/", "\")

if (-not (Test-Path -LiteralPath $LayoutWin)) {
  throw "Missing layout scout artifact: $LayoutWin. Run scripts\run_cuprate_2d_4x4_layout_scout_wsl.ps1 first."
}

$BestSeed = (Get-Content -Raw -LiteralPath $LayoutWin | ConvertFrom-Json).best_candidate.seed_transpiler

wsl.exe --cd "$RepoWsl" "$Python" "cuprate_2d_ibm_hardware_runner.py" `
  --config "$RunDir/cuprate_2d_config.json" `
  --outdir "$OutDir" `
  --backend "ibm_marrakesh" `
  --steps 1 `
  --shots 1024 `
  --circuit-family "number_preserving_t_only" `
  --readout-repetitions 3 `
  --readout-shots 4096 `
  --optimization-level 1 `
  --seed-transpiler "$BestSeed" `
  --wait-seconds 0 `
  --poll-interval 30 `
  --submit
