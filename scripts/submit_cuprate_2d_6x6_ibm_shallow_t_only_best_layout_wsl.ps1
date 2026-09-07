$ErrorActionPreference = "Stop"

$RepoWin = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$RepoWinForWsl = $RepoWin -replace "\\", "/"
$RepoWsl = (wsl.exe wslpath -a "$RepoWinForWsl").Trim()
$Python = "/home/bram/.venvs/qiskit/bin/python"
$Backend = "ibm_marrakesh"
$RunDir = "results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1"
$OutDir = "$RunDir/ibm_hardware_steps1_shallow_t_only_best_layout"
$Layout = "$RunDir/layout_scout_shallow_t_only/best_layout.json"
$LayoutWin = Join-Path $RepoWin ($Layout -replace "/", "\")

if (-not (Test-Path -LiteralPath $LayoutWin)) {
  throw "Missing layout scout artifact: $LayoutWin. Run scripts\run_cuprate_2d_6x6_layout_scout_wsl.ps1 first."
}

wsl.exe --cd "$RepoWsl" "$Python" "cuprate_2d_ibm_hardware_runner.py" `
  --config "$RunDir/cuprate_2d_config.json" `
  --outdir "$OutDir" `
  --backend "$Backend" `
  --steps 1 `
  --shots 1024 `
  --circuit-family "number_preserving_t_only" `
  --readout-repetitions 3 `
  --readout-shots 4096 `
  --optimization-level 1 `
  --initial-layout "$Layout" `
  --use-layout-seed `
  --wait-seconds 0 `
  --poll-interval 30 `
  --submit
