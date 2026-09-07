$ErrorActionPreference = "Stop"

$RepoWin = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$RepoWinForWsl = $RepoWin -replace "\\", "/"
$RepoWsl = (wsl.exe wslpath -a "$RepoWinForWsl").Trim()
$Python = "/home/bram/.venvs/qiskit/bin/python"
$RunDir = "results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111"
$OutDir = "$RunDir/ibm_hardware_steps1_best_layout_plan"
$Layout = "$RunDir/layout_scout/best_layout.json"
$LayoutWin = Join-Path $RepoWin ($Layout -replace "/", "\")
$BestSeed = (Get-Content -Raw -LiteralPath $LayoutWin | ConvertFrom-Json).best_candidate.seed_transpiler

wsl.exe --cd "$RepoWsl" "$Python" "cuprate_2d_ibm_hardware_runner.py" `
  --config "$RunDir/cuprate_2d_config.json" `
  --outdir "$OutDir" `
  --backend "ibm_marrakesh" `
  --steps 1 `
  --shots 512 `
  --readout-repetitions 3 `
  --readout-shots 4096 `
  --optimization-level 1 `
  --seed-transpiler "$BestSeed" `
  --wait-seconds 0 `
  --poll-interval 30
