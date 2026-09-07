$ErrorActionPreference = "Stop"

$RepoWin = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$RepoWinForWsl = $RepoWin -replace "\\", "/"
$RepoWsl = (wsl.exe wslpath -a "$RepoWinForWsl").Trim()
$Python = "/home/bram/.venvs/qiskit/bin/python"

wsl.exe --cd "$RepoWsl" "$Python" "cuprate_2d_hubbard_pipeline.py" `
  --lx 6 --ly 6 `
  --holes 4 `
  --U-over-t 8 `
  --t-prime-over-t -0.25 `
  --steps 4 `
  --dt 0.1 `
  --initial-state stripe_neel `
  --outdir "results_cuprate_2d/cuprate_6x6_u8_tp-0p25_holes4_doping0p111"
