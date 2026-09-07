$ErrorActionPreference = "Stop"

$RepoWin = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$Drive = $RepoWin.Substring(0, 1).ToLowerInvariant()
$Tail = $RepoWin.Substring(2).Replace([char]92, [char]47)
$RepoWsl = "/mnt/$Drive$Tail"
$Python = "/home/bram/.venvs/qiskit/bin/python"
$RunDir = "results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111"
$OutDir = "$RunDir/fire_opal_steps1_best_mit"
$QctrlNotebook = "/mnt/c/Users/Lenna/SynologyDrive/stackexchange/get-started-with-fire-opal-on-ibm-quantum.ipynb"

wsl.exe --cd "$RepoWsl" "$Python" "cuprate_2d_fire_opal_runner.py" `
  --config "$RunDir/cuprate_2d_config.json" `
  --outdir "$OutDir" `
  --backend "ibm_marrakesh" `
  --steps 1 `
  --shots 1024 `
  --readout-shots 4096 `
  --qctrl-notebook "$QctrlNotebook" `
  --abstract-input `
  --submit
