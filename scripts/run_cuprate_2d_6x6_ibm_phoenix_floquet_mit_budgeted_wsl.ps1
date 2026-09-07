param(
  [ValidateRange(1, 1000000)]
  [int]$Shots = 128,

  [ValidateRange(1, 10800)]
  [int]$MaxExecutionTime = 5,

  [ValidateRange(1, 100)]
  [int]$SeedCount = 12,

  [ValidateRange(1, 1024)]
  [int]$TwirlRandomizations = 4,

  [switch]$Submit
)

$ErrorActionPreference = "Stop"

if ($Shots % $TwirlRandomizations -ne 0) {
  throw "Shots must be divisible by TwirlRandomizations."
}

$TwirlShots = [int]($Shots / $TwirlRandomizations)
$RepoWin = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$RepoWinForWsl = $RepoWin -replace "\\", "/"
$RepoWsl = (wsl.exe wslpath -a "$RepoWinForWsl").Trim()
$Python = "/home/bram/.venvs/qiskit/bin/python"
$AccountName = "qiskit-runtime-q9"
$Backend = "ibm_phoenix"
$RunDir = "results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1"
$LayoutDir = "$RunDir/layout_scout_shallow_t_only_ibm_phoenix"
$OutDir = "$RunDir/ibm_phoenix_floquet_xy4_twirling_s${Shots}_max${MaxExecutionTime}s"

& wsl.exe --cd "$RepoWsl" "$Python" "cuprate_2d_layout_scout.py" `
  --config "$RunDir/cuprate_2d_config.json" `
  --outdir "$LayoutDir" `
  --backend "$Backend" `
  --account-name "$AccountName" `
  --steps 1 `
  --circuit-family "number_preserving_t_only" `
  --optimization-level 1 `
  --seed-start 1 `
  --seed-count "$SeedCount" `
  --include-readout

if ($LASTEXITCODE -ne 0) {
  throw "Phoenix layout scout failed with exit code $LASTEXITCODE."
}

$LayoutWin = Join-Path $RepoWin (($LayoutDir + "/best_layout.json") -replace "/", "\")
$LayoutPayload = Get-Content -LiteralPath $LayoutWin -Raw | ConvertFrom-Json
$Seed = [int]$LayoutPayload.recommended_runner_args.seed_transpiler

$RunnerArgs = @(
  "cuprate_2d_ibm_hardware_runner.py",
  "--config", "$RunDir/cuprate_2d_config.json",
  "--outdir", $OutDir,
  "--backend", $Backend,
  "--account-name", $AccountName,
  "--steps", "1",
  "--shots", "$Shots",
  "--circuit-family", "number_preserving_t_only",
  "--readout-repetitions", "1",
  "--readout-shots", "$Shots",
  "--optimization-level", "1",
  "--seed-transpiler", "$Seed",
  "--max-execution-time", "$MaxExecutionTime",
  "--dd-sequence", "XY4",
  "--twirl-randomizations", "$TwirlRandomizations",
  "--twirl-shots-per-randomization", "$TwirlShots",
  "--job-tag", "2d-cuprate-phoenix-floquet-xy4-twirling",
  "--wait-seconds", "0",
  "--poll-interval", "30"
)

if ($Submit) {
  $SubmittedWin = Join-Path $RepoWin (($OutDir + "/submitted_jobs.json") -replace "/", "\")
  if (Test-Path -LiteralPath $SubmittedWin) {
    throw "Refusing duplicate submission: $SubmittedWin already exists."
  }
  $RunnerArgs += "--submit"
}

& wsl.exe --cd "$RepoWsl" "$Python" @RunnerArgs

if ($LASTEXITCODE -ne 0) {
  throw "Phoenix Floquet-mitigation runner failed with exit code $LASTEXITCODE."
}

if (-not $Submit) {
  Write-Output "Dry-run complete. No IBM job submitted."
  Write-Output "Profile: XY4 + gate twirling + layout-matched readout calibration."
}
