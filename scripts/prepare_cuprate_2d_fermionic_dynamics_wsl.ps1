param([switch]$RoutePhoenix)
$ErrorActionPreference = 'Stop'
$RepoWin = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$RepoWsl = (& wsl.exe -d Ubuntu-Preview-C -- wslpath -a ($RepoWin -replace '\\','/')).Trim()
$PythonPath = '/home/bram/.venvs/qiskit/bin/python'
$OutputBase = 'results_cuprate_2d/fermionic_dynamics_2026-09-05'
& wsl.exe -d Ubuntu-Preview-C --cd $RepoWsl $PythonPath validate_cuprate_2d_fermionic_dynamics.py --outdir "$OutputBase/validation"
if ($LASTEXITCODE -ne 0) { throw 'Fermionic numerical validation failed' }
$RunnerArgs = @('prepare_cuprate_2d_fermionic_sweep.py',
    '--config','results_cuprate_2d/validation_ladder_steps1/cuprate_6x6_holes4_steps1/cuprate_2d_config.json',
    '--validation',"$OutputBase/validation/validation.json",'--outdir',"$OutputBase/sweep",
    '--steps','2','4','8','--shots','512','--max-execution-time','5')
if ($RoutePhoenix) { $RunnerArgs += @('--backend','ibm_phoenix','--account-name','qiskit-runtime-q9') }
& wsl.exe -d Ubuntu-Preview-C --cd $RepoWsl $PythonPath @RunnerArgs
if ($LASTEXITCODE -ne 0) { throw 'Fermionic sweep preparation failed' }
