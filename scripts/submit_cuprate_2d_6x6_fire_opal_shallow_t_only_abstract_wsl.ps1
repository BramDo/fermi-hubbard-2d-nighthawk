$ErrorActionPreference = "Stop"

$RepoWin = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$RepoWinForWsl = $RepoWin -replace "\\", "/"
$RepoWsl = (wsl.exe wslpath -a "$RepoWinForWsl").Trim()
$Python = "/home/bram/.venvs/qiskit/bin/python"
$Backend = "ibm_marrakesh"
$RunDir = "results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1"
$OutDir = "$RunDir/fire_opal_shallow_t_only_abstract"
$QctrlNotebook = "/mnt/c/Users/Lenna/SynologyDrive/stackexchange/get-started-with-fire-opal-on-ibm-quantum.ipynb"

wsl.exe --cd "$RepoWsl" "$Python" "cuprate_2d_fire_opal_runner.py" `
  --config "$RunDir/cuprate_2d_config.json" `
  --outdir "$OutDir" `
  --backend "$Backend" `
  --steps 1 `
  --shots 1024 `
  --readout-shots 4096 `
  --circuit-family "number_preserving_t_only" `
  --abstract-input `
  --qctrl-notebook "$QctrlNotebook" `
  --submit
