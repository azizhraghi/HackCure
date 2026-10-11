param([switch]$NoBrowser, [ValidateSet('stub','live','off')][string]$AiMode = 'stub')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$cache = Join-Path $projectRoot 'backend/.cache'
$dotnet = Join-Path $cache 'tools/dotnet/dotnet.exe'
$python = Join-Path $projectRoot 'backend/.venv/Scripts/python.exe'
$mongo = Get-Item (Join-Path $cache 'tools/mongodb-installed/bin/mongod.exe') -ErrorAction SilentlyContinue
if (!$mongo) { $mongo = Get-ChildItem (Join-Path $cache 'tools/mongodb') -Filter mongod.exe -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1 }
if (!(Test-Path $dotnet) -or !(Test-Path $python) -or !$mongo) {
    throw 'Local runtimes missing. See README.md for .NET 8, MongoDB 7 and Python setup.'
}
New-Item -ItemType Directory -Force (Join-Path $cache 'mongo-data') | Out-Null
function Test-Health($url) {
    try { return (Invoke-WebRequest $url -TimeoutSec 3 -UseBasicParsing).StatusCode -eq 200 }
    catch { return $false }
}
function Wait-Health($url, $log) {
    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        if (Test-Health $url) { return }
        Start-Sleep -Seconds 2
    }
    throw "Service did not become ready: $url. See $log"
}
$mongoPortOpen = $false
$socket = [System.Net.Sockets.TcpClient]::new()
try { $socket.Connect('127.0.0.1', 27017); $mongoPortOpen = $true } catch {} finally { $socket.Dispose() }
if (!$mongoPortOpen) {
    Start-Process -FilePath $mongo.FullName -WindowStyle Hidden -ArgumentList @('--bind_ip','127.0.0.1','--port','27017','--dbpath',('"' + (Join-Path $cache 'mongo-data') + '"'),'--logpath',('"' + (Join-Path $cache 'mongo.log') + '"'),'--logappend') | Out-Null
}
$env:DOTNET_ROOT = Split-Path $dotnet
$env:DOTNET_CLI_TELEMETRY_OPTOUT = '1'
$env:ASPNETCORE_URLS = 'http://127.0.0.1:8080'
$env:MongoDbSettings__ConnectionString = 'mongodb://127.0.0.1:27017'
$env:MongoDbSettings__DatabaseName = 'DB_story'
$env:Mqtt__Enabled = 'false'
$env:WhatsApp__Enabled = 'false'
$env:Firebase__Enabled = 'false'
$env:EnableSwagger = 'true'
$env:Jwt__Key = 'local-fictional-demo-only-key-32-characters'
$env:Auth__StaffRegistrationCode = 'STAFF-2026'
$env:ServiceApiKeys__Agents = 'dev-agents-key'
$env:ServiceApiKeys__Iot = 'dev-iot-key'
$env:ChatService__BaseUrl = 'http://127.0.0.1:8000'
if (!(Test-Health 'http://127.0.0.1:8080/health')) {
    Start-Process -FilePath $dotnet -WindowStyle Hidden -WorkingDirectory (Join-Path $projectRoot 'SurgiGuard/Backend/API') -ArgumentList @('run','--no-launch-profile') -RedirectStandardOutput (Join-Path $cache 'api.log') -RedirectStandardError (Join-Path $cache 'api-error.log') | Out-Null
    Wait-Health 'http://127.0.0.1:8080/health' (Join-Path $cache 'api.log')
}
& $python (Join-Path $projectRoot 'SurgiGuard/Backend/scripts/seed_story.py') --api http://127.0.0.1:8080
if ($LASTEXITCODE -ne 0) { throw 'Demo account creation failed.' }
$env:SURGIGUARD_API_URL = 'http://127.0.0.1:8080'
$env:LLM_MODE = $AiMode
if (!(Test-Health 'http://127.0.0.1:8000/hub/status')) {
    Start-Process -FilePath $python -WindowStyle Hidden -WorkingDirectory (Join-Path $projectRoot 'backend') -ArgumentList @('-m','uvicorn','main:app','--host','127.0.0.1','--port','8000') -RedirectStandardOutput (Join-Path $cache 'ai.log') -RedirectStandardError (Join-Path $cache 'ai-error.log') | Out-Null
    Wait-Health 'http://127.0.0.1:8000/hub/status' (Join-Path $cache 'ai-error.log')
}
# Apply the requested mode when reusing an already running AI service too.
Invoke-RestMethod -Uri "http://127.0.0.1:8000/demo/llm_mode/$AiMode" -Method Post | Out-Null
Write-Host 'Ready: http://localhost:8000/story (integration), http://localhost:8000/app/ (patient app)'
Write-Host "Demo database: DB_story. MQTT and external notifications disabled. AI mode: $AiMode."
if (!$NoBrowser) { Start-Process 'http://localhost:8000/story' }
