$ErrorActionPreference = "Stop"

$RepoWin = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$Drive = $RepoWin.Substring(0, 1).ToLowerInvariant()
$Tail = $RepoWin.Substring(2).Replace([char]92, [char]47)
$RepoWsl = "/mnt/$Drive$Tail"
$Python = "/home/bram/.venvs/qiskit/bin/python"

wsl.exe --cd "$RepoWsl" "$Python" "cuprate_2d_validation_ladder.py" `
  --outdir "results_cuprate_2d/validation_3x3_steps1" `
  --only "3x3" `
  --target-doping 0.1111111111111111 `
  --backend "ibm_marrakesh" `
  --shots 1024 `
  --readout-shots 4096
