param(
  [ValidateSet("PEC", "ZNE", "Both")]
  [string]$Method = "Both",

  [ValidateRange(1, 1000000)]
  [int]$Shots = 128,

  [ValidateRange(1, 10800)]
  [int]$MaxExecutionTime = 5,

  [switch]$Submit
)

$ErrorActionPreference = "Stop"
if ($Submit -and $Method -eq "Both") {
  throw "Submit PEC and ZNE separately so each paid job receives explicit authorization."
}

$RepoWin = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$RepoWinForWsl = $RepoWin -replace "\\", "/"
$RepoWsl = (wsl.exe wslpath -a "$RepoWinForWsl").Trim()
$Python = "/home/bram/.venvs/qiskit/bin/python"
$RunDir = "results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1"
$Methods = if ($Method -eq "Both") { @("pec", "zne") } else { @($Method.ToLowerInvariant()) }

foreach ($CurrentMethod in $Methods) {
  $OutDir = "$RunDir/ibm_phoenix_${CurrentMethod}_estimator_s${Shots}_max${MaxExecutionTime}s"
  $RunnerArgs = @(
    "cuprate_2d_pec_zne_runner.py",
    "--config", "$RunDir/cuprate_2d_config.json",
    "--outdir", $OutDir,
    "--method", $CurrentMethod,
    "--backend", "ibm_phoenix",
    "--account-name", "qiskit-runtime-q9",
    "--shots", "$Shots",
    "--max-execution-time", "$MaxExecutionTime",
    "--optimization-level", "1",
    "--seed-transpiler", "9"
  )
  if ($Submit) {
    $RunnerArgs += "--submit"
  }
  & wsl.exe --cd "$RepoWsl" "$Python" @RunnerArgs
  if ($LASTEXITCODE -ne 0) {
    throw "$CurrentMethod runner failed with exit code $LASTEXITCODE."
  }
}

if (-not $Submit) {
  Write-Output "PEC/ZNE dry-run complete. No IBM job submitted."
}
