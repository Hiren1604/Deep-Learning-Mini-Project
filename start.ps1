$ErrorActionPreference = 'Stop'
$projectDirectory = $PSScriptRoot
$pythonExecutable = Join-Path $projectDirectory '.venv\Scripts\python.exe'
$logDirectory = Join-Path $projectDirectory '.cache'
if (-not (Test-Path -LiteralPath $pythonExecutable)) {
    throw 'Create .venv and install requirements first. See README.md.'
}
if (-not (Test-Path -LiteralPath (Join-Path $projectDirectory 'data\cleaned_products.csv'))) {
    throw 'Run .venv\Scripts\python.exe setup_data.py first.'
}
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
foreach ($service in @(
    @{ Name = 'backend'; Port = 8000; Arguments = '-m uvicorn src.api:app --host 127.0.0.1 --port 8000' },
    @{ Name = 'frontend'; Port = 8501; Arguments = '-m streamlit run src/ui.py --server.address 127.0.0.1 --server.port 8501 --server.headless true --browser.gatherUsageStats false' }
)) {
    $portInUse = $false
    $connection = New-Object System.Net.Sockets.TcpClient
    try {
        $connection.Connect('127.0.0.1', $service.Port)
        $portInUse = $true
    } catch [System.Net.Sockets.SocketException] {
        $portInUse = $false
    } finally {
        $connection.Dispose()
    }
    if ($portInUse) {
        Write-Host "Port $($service.Port) is already in use; skipped $($service.Name)."
        continue
    }
    $process = Start-Process -FilePath $pythonExecutable -ArgumentList $service.Arguments `
        -WorkingDirectory $projectDirectory -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $logDirectory "$($service.Name).log") `
        -RedirectStandardError (Join-Path $logDirectory "$($service.Name).error.log")
    Set-Content -LiteralPath (Join-Path $logDirectory "$($service.Name).pid") -Value $process.Id
    Write-Host "Started $($service.Name) (PID $($process.Id))."
}
Write-Host 'UI: http://localhost:8501'
Write-Host 'API docs: http://127.0.0.1:8000/docs'
Write-Host 'Logs: .cache\backend.error.log and .cache\frontend.error.log'
