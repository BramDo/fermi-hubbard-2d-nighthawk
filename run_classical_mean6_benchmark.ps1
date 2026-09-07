$ErrorActionPreference = 'Stop'
$taskRoot = $PSScriptRoot
$taskRootForWsl = $taskRoot -replace '\\', '/'
$taskWslRoot = (wsl.exe -d Ubuntu-Preview-C wslpath -a $taskRootForWsl).Trim()
if ($LASTEXITCODE -ne 0 -or -not $taskWslRoot) { throw 'Cannot resolve this repository in WSL' }
$taskRun = Join-Path $taskRoot 'results_cuprate_2d\classical_mean6_timing_2026-09-06_v1'
if (Test-Path -LiteralPath $taskRun) { throw 'Benchmark output exists; preserve it and stop' }
$null = New-Item -ItemType Directory -Path $taskRun

function Write-ExclusiveJson($Path, $Value) {
    $taskText = ($Value | ConvertTo-Json -Depth 90) + "`n"
    $taskStream = [System.IO.File]::Open($Path,[System.IO.FileMode]::CreateNew,[System.IO.FileAccess]::Write)
    try {
        $taskBytes = [System.Text.Encoding]::UTF8.GetBytes($taskText)
        $taskStream.Write($taskBytes,0,$taskBytes.Length)
    } finally { $taskStream.Dispose() }
}

function Invoke-BoundedPython([string[]]$PythonArgs) {
    $taskInfo = [System.Diagnostics.ProcessStartInfo]::new()
    $taskInfo.FileName = 'wsl.exe'
    $taskInfo.UseShellExecute = $false
    $taskInfo.CreateNoWindow = $true
    $taskInfo.RedirectStandardOutput = $true
    $taskInfo.RedirectStandardError = $true
    $taskArguments = @('-d','Ubuntu-Preview-C','--cd',$taskWslRoot,
        'timeout','25s','env','OPENBLAS_NUM_THREADS=1','OMP_NUM_THREADS=1','MKL_NUM_THREADS=1','NUMEXPR_NUM_THREADS=1',
        'PYTHONDONTWRITEBYTECODE=1','/home/bram/.venvs/qiskit/bin/python','-B','-u') + $PythonArgs
    foreach ($taskArgument in $taskArguments) { $taskInfo.ArgumentList.Add($taskArgument) }
    $taskProcess = [System.Diagnostics.Process]::new()
    $taskProcess.StartInfo = $taskInfo
    $taskClock = [System.Diagnostics.Stopwatch]::StartNew()
    $null = $taskProcess.Start()
    $taskOutput = $taskProcess.StandardOutput.ReadToEndAsync()
    $taskError = $taskProcess.StandardError.ReadToEndAsync()
    if (-not $taskProcess.WaitForExit(30000)) {
        $taskProcess.Kill()
        throw 'Windows timeout; WSL command also has its own 25-second timeout'
    }
    $taskOutputText = $taskOutput.GetAwaiter().GetResult()
    $taskErrorText = $taskError.GetAwaiter().GetResult()
    $taskClock.Stop()
    $taskReturnCode = $taskProcess.ExitCode
    $taskProcess.Dispose()
    return [PSCustomObject]@{ returncode=$taskReturnCode; windows_call_seconds=$taskClock.Elapsed.TotalSeconds;
        stdout=$taskOutputText; stderr=$taskErrorText }
}

$taskSources = @('CLASSICAL_MEAN6_BENCHMARK_PROTOCOL.md','benchmark_classical_mean6.py',
    'test_classical_mean6.py','run_classical_mean6_benchmark.ps1','cuprate_2d_tflo.py',
    'cuprate_2d_hubbard_pipeline.py','cuprate_2d_fermionic_mapping.py','cuprate_2d_fermionic_dynamics.py')
$taskHashes = [ordered]@{}
$taskSnapshot = Join-Path $taskRun 'source_snapshot'
$null = New-Item -ItemType Directory -Path $taskSnapshot
foreach ($taskName in $taskSources) {
    $taskPath = Join-Path $taskRoot $taskName
    $taskHashes[$taskName] = (Get-FileHash -LiteralPath $taskPath -Algorithm SHA256).Hash.ToLowerInvariant()
    Copy-Item -LiteralPath $taskPath -Destination (Join-Path $taskSnapshot $taskName)
}
Write-ExclusiveJson (Join-Path $taskRun 'source_sha256.json') $taskHashes
$taskEnvironment = [ordered]@{ started_utc=[DateTime]::UtcNow.ToString('o');
    repetitions=5; sequential=$true; fresh_python_processes=$true; os_caches_flushed=$false;
    other_machine_load_controlled=$false; powershell_version=$PSVersionTable.PSVersion.ToString();
    cpu=@(Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors);
    whole_machine_cpu_percent_before=(Get-CimInstance Win32_PerfFormattedData_PerfOS_Processor | Where-Object Name -EQ '_Total').PercentProcessorTime }
Write-ExclusiveJson (Join-Path $taskRun 'environment.json') $taskEnvironment

$taskTests = Invoke-BoundedPython @('test_classical_mean6.py','-v')
Write-ExclusiveJson (Join-Path $taskRun 'tests.json') $taskTests
if ($taskTests.returncode -ne 0) { Write-Output $taskTests.stderr; throw 'Tests failed before timing; do not continue' }
Write-Output 'Six local tests passed; beginning five fresh-process timing repetitions.'
$taskRuns = @()
for ($taskIndex=0; $taskIndex -lt 5; $taskIndex++) {
    $taskTimed = Invoke-BoundedPython @('benchmark_classical_mean6.py','worker')
    if ($taskTimed.returncode -ne 0) {
        Write-ExclusiveJson (Join-Path $taskRun "failed_worker_$taskIndex.json") $taskTimed
        Write-Output $taskTimed.stderr
        throw 'Worker failed; retain diagnostics and stop'
    }
    $taskWorker = $taskTimed.stdout | ConvertFrom-Json
    $taskRecord = [ordered]@{ index=$taskIndex; returncode=$taskTimed.returncode;
        windows_call_seconds=$taskTimed.windows_call_seconds; stderr=$taskTimed.stderr; worker=$taskWorker }
    Write-ExclusiveJson (Join-Path $taskRun "worker_$taskIndex.json") $taskRecord
    $taskRuns += $taskRecord
    Write-Output ("Run {0}: kernel={1:F6}s; Python-ready={2:F6}s; Windows-call={3:F6}s" -f
        $taskIndex,$taskWorker.kernel_seconds,$taskWorker.python_to_result_ready_seconds,$taskTimed.windows_call_seconds)
}
Write-ExclusiveJson (Join-Path $taskRun 'windows_timings.json') ([ordered]@{
    method='Stopwatch from Process.Start through stdout/stderr completion and process exit; includes WSL and Python startup, six newly computed references, checks and JSON output';
    runs=$taskRuns; ended_utc=[DateTime]::UtcNow.ToString('o') })
$taskAnalysis = Invoke-BoundedPython @('benchmark_classical_mean6.py','analyze')
Write-ExclusiveJson (Join-Path $taskRun 'analysis_process.json') $taskAnalysis
if ($taskAnalysis.returncode -ne 0) { Write-Output $taskAnalysis.stderr; throw 'Analysis failed' }
Write-Output $taskAnalysis.stdout
