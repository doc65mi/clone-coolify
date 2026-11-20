param([switch]$OpenBrowser)
$ErrorActionPreference = 'Stop'
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$expectedVersion = (Get-Content -LiteralPath (Join-Path $projectRoot 'VERSION') -Raw).Trim()
$envPath = Join-Path $projectRoot '.env'
$port = 8787
if (Test-Path -LiteralPath $envPath) {
    foreach ($line in Get-Content -LiteralPath $envPath) {
        if ($line -match '^CLONE_PORT=(\d+)$') { $port = [int]$Matches[1] }
    }
}
$url = 'http://127.0.0.1:' + $port
function Get-CloneHealth {
    try { return Invoke-RestMethod -Uri ($url + '/health') -TimeoutSec 2 -ErrorAction Stop } catch { return $null }
}
$health = Get-CloneHealth
if ($health) {
    if ($health.product -ne 'clone-coolify' -or $health.version -ne $expectedVersion) {
        throw "La porta $port è occupata da un'altra applicazione o versione. Non è stato fermato alcun processo."
    }
    Write-Output ('Applicazione già avviata: ' + $url + ' (v' + $health.version + ')')
    if ($OpenBrowser) { Start-Process $url }
    exit 0
}
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    $pythonCommand = Get-Command python.exe -ErrorAction SilentlyContinue
    if (-not $pythonCommand) { throw 'Python non trovato. Installare Python 3.11+ oppure usare Docker come descritto nel manuale.' }
    $pythonPath = $pythonCommand.Source
}
& $pythonPath -c 'import fastapi, uvicorn, httpx, cryptography' 2>$null
if ($LASTEXITCODE -ne 0) { throw 'Dipendenze mancanti. Dalla cartella progetto eseguire: python -m pip install -r requirements.txt' }
if (-not (Test-Path -LiteralPath $envPath)) {
    & $pythonPath (Join-Path $projectRoot 'tools\setup.py')
    if ($LASTEXITCODE -ne 0) { throw 'Configurazione iniziale non riuscita.' }
}
$logDir = Join-Path $projectRoot 'data'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$outLog = Join-Path $logDir 'server-out.log'
$errLog = Join-Path $logDir 'server-error.log'
$process = Start-Process -FilePath $pythonPath -ArgumentList @('tools/run.py') -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput $outLog -RedirectStandardError $errLog -PassThru
for ($attempt = 0; $attempt -lt 25; $attempt++) {
    Start-Sleep -Milliseconds 400
    $health = Get-CloneHealth
    if ($health -and $health.product -eq 'clone-coolify' -and $health.version -eq $expectedVersion) {
        Set-Content -LiteralPath (Join-Path $logDir 'server.pid') -Value $process.Id
        Write-Output ('Applicazione avviata: ' + $url + ' (v' + $health.version + ')')
        Write-Output ('Log: ' + $errLog)
        if ($OpenBrowser) { Start-Process $url }
        exit 0
    }
    $process.Refresh()
    if ($process.HasExited) { throw ('Il backend si è fermato. Consultare ' + $errLog) }
}
throw ('Avvio non confermato. Consultare ' + $errLog)
