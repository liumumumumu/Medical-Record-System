param(
    [int]$AiPort = 5000,
    [int]$BackendPort = 8080,
    [int]$FrontendPort = 5173,
    [string]$MongoDatabase = "medical_records",
    [switch]$EnableDemoUser,
    [switch]$OpenBrowser,
    [switch]$ForceRebuild
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$Root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$Runtime = Join-Path $Root ".runtime"
$Logs = Join-Path $Runtime "logs"
$PidFile = Join-Path $Runtime "pids.json"
$FrontendBuildState = Join-Path $Runtime "frontend-build.json"
$DemoUsername = "demo"
$DemoPassword = "demo123456"

. (Join-Path $PSScriptRoot "runtime-process.ps1")

New-Item -ItemType Directory -Force -Path $Logs | Out-Null

function Write-Step([string]$Message) {
    Write-Host "[启动] $Message" -ForegroundColor Cyan
}

function Test-Port([int]$Port) {
    return [bool](Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue)
}

function Get-PortOwnerDescription([int]$Port) {
    $connection = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $connection) { return "未知进程" }
    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$([int]$connection.OwningProcess)" -ErrorAction SilentlyContinue
    if ($null -eq $process) { return "PID $($connection.OwningProcess)" }
    return "$($process.Name)（PID $($process.ProcessId)）"
}

function Wait-Http([string]$Url, [int]$Seconds, $ProcessRecord) {
    $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        if ($null -ne $ProcessRecord -and -not (Test-TrackedProcessIdentity $ProcessRecord)) {
            throw "服务进程提前退出：$($ProcessRecord.service)。请查看日志目录 $Logs。"
        }
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) { return }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    throw "服务未在 $Seconds 秒内就绪：$Url。请查看日志目录 $Logs。"
}

function Test-BuildRequired([string]$OutputPath, [string[]]$InputPaths) {
    if ($ForceRebuild -or -not (Test-Path -LiteralPath $OutputPath)) { return $true }
    $outputTime = (Get-Item -LiteralPath $OutputPath).LastWriteTimeUtc

    foreach ($path in $InputPaths) {
        if (-not (Test-Path -LiteralPath $path)) { continue }
        $item = Get-Item -LiteralPath $path
        if (-not $item.PSIsContainer) {
            if ($item.LastWriteTimeUtc -gt $outputTime) { return $true }
            continue
        }
        $newerFile = Get-ChildItem -LiteralPath $path -Recurse -File -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTimeUtc -gt $outputTime } |
            Select-Object -First 1
        if ($null -ne $newerFile) { return $true }
    }
    return $false
}

function Remove-ExistingTrackedState {
    if (-not (Test-Path -LiteralPath $PidFile)) { return $false }

    try {
        $state = Get-Content -Raw -LiteralPath $PidFile | ConvertFrom-Json
    } catch {
        Remove-Item -LiteralPath $PidFile -Force
        Write-Warning "发现无法读取的旧启动记录，已安全忽略；没有结束任何进程。"
        return $false
    }

    if ([int]$state.schemaVersion -ne 2 -or $null -eq $state.processes) {
        Remove-Item -LiteralPath $PidFile -Force
        Write-Warning "发现旧版启动记录，已安全忽略；没有按旧 PID 结束任何进程。"
        return $false
    }

    $records = @($state.processes.frontend, $state.processes.backend, $state.processes.ai)
    $allRunning = $true
    foreach ($record in $records) {
        if ($null -eq $record -or -not (Test-TrackedProcessIdentity $record)) { $allRunning = $false }
    }
    $sameConfiguration =
        [int]$state.ports.ai -eq $AiPort -and
        [int]$state.ports.backend -eq $BackendPort -and
        [int]$state.ports.frontend -eq $FrontendPort -and
        [string]$state.mongoDatabase -eq $MongoDatabase

    if ($allRunning -and $sameConfiguration) {
        Write-Host "系统已经在运行，无需重复启动。" -ForegroundColor Green
        if ($OpenBrowser) { Start-Process "http://127.0.0.1:$FrontendPort/" }
        return $true
    }

    Write-Step "清理上一次未完整结束的本项目进程"
    foreach ($record in $records) {
        if ($null -eq $record) { continue }
        $result = Stop-TrackedProcess $record
        if ($result -eq "IdentityMismatch") {
            Write-Warning "$($record.service) 的 PID 已被其他程序复用，已跳过，未结束该进程。"
        }
    }
    Remove-Item -LiteralPath $PidFile -Force
    Start-Sleep -Milliseconds 500
    return $false
}

if (Remove-ExistingTrackedState) { exit 0 }

Write-Step "检查 Java、Python、Node.js 和 MongoDB"
$python = (Get-Command python -ErrorAction Stop).Source
$node = (Get-Command node -ErrorAction Stop).Source
$npm = (Get-Command npm.cmd -ErrorAction Stop).Source
$java = (Get-Command java -ErrorAction Stop).Source
$maven = Join-Path $Root "代码文件\backend-service\mvnw.cmd"
$viteCli = Join-Path $Root "代码文件\frontend\frontend\node_modules\vite\bin\vite.js"
if (-not (Test-Path -LiteralPath $maven)) { throw "未找到 Maven Wrapper：$maven" }
if (-not (Test-Path -LiteralPath $viteCli)) { throw "前端依赖尚未安装，请先在前端目录运行 npm install。" }

if (-not (Test-Port 27017)) {
    $mongoService = Get-Service -Name MongoDB -ErrorAction SilentlyContinue
    if (-not $mongoService) { throw "未找到 MongoDB 服务，请先安装 MongoDB。" }
    try { Start-Service -Name MongoDB } catch { throw "MongoDB 未启动，请以管理员身份启动 MongoDB 服务后重试。原始错误：$($_.Exception.Message)" }
    $deadline = [DateTime]::UtcNow.AddSeconds(20)
    while (-not (Test-Port 27017) -and [DateTime]::UtcNow -lt $deadline) { Start-Sleep -Milliseconds 500 }
    if (-not (Test-Port 27017)) { throw "MongoDB 未能在 27017 端口启动。" }
}

foreach ($port in @($AiPort, $BackendPort, $FrontendPort)) {
    if (Test-Port $port) {
        throw "端口 $port 已被 $(Get-PortOwnerDescription $port) 占用。请关闭冲突程序后重试。"
    }
}

$secretFile = Join-Path $Runtime "jwt-secret.txt"
if (-not (Test-Path -LiteralPath $secretFile)) {
    $bytes = New-Object byte[] 48
    $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $generator.GetBytes($bytes) } finally { $generator.Dispose() }
    [IO.File]::WriteAllText($secretFile, [Convert]::ToBase64String($bytes), [Text.Encoding]::UTF8)
}
$jwtSecret = [IO.File]::ReadAllText($secretFile, [Text.Encoding]::UTF8).Trim()

$backendDir = Join-Path $Root "代码文件\backend-service"
$backendJar = Join-Path $backendDir "target\backend-0.0.1-SNAPSHOT.jar"
$backendInputs = @((Join-Path $backendDir "pom.xml"), (Join-Path $backendDir "src"))
if (Test-BuildRequired -OutputPath $backendJar -InputPaths $backendInputs) {
    Write-Step "后端代码有变化，正在构建一次性演示包"
    Push-Location $backendDir
    try {
        & $maven "-DskipTests" "package"
        if ($LASTEXITCODE -ne 0) { throw "后端构建失败（退出码 $LASTEXITCODE）。" }
    } finally { Pop-Location }
} else {
    Write-Step "复用已构建的后端演示包"
}
if (-not (Test-Path -LiteralPath $backendJar)) { throw "后端构建产物不存在：$backendJar" }

$frontendDir = Join-Path $Root "代码文件\frontend\frontend"
$frontendOutput = Join-Path $frontendDir "dist\index.html"
$frontendInputs = @(
    (Join-Path $frontendDir "src"),
    (Join-Path $frontendDir "public"),
    (Join-Path $frontendDir "package.json"),
    (Join-Path $frontendDir "package-lock.json"),
    (Join-Path $frontendDir "vite.config.ts"),
    (Join-Path $frontendDir "tsconfig.json"),
    (Join-Path $frontendDir "tsconfig.app.json")
)
$apiBaseUrl = "http://127.0.0.1:$BackendPort"
$frontendNeedsBuild = Test-BuildRequired -OutputPath $frontendOutput -InputPaths $frontendInputs
if (-not $frontendNeedsBuild -and (Test-Path -LiteralPath $FrontendBuildState)) {
    try {
        $buildState = Get-Content -Raw -LiteralPath $FrontendBuildState | ConvertFrom-Json
        if ([string]$buildState.apiBaseUrl -ne $apiBaseUrl) { $frontendNeedsBuild = $true }
    } catch { $frontendNeedsBuild = $true }
} elseif (-not (Test-Path -LiteralPath $FrontendBuildState)) {
    $frontendNeedsBuild = $true
}

if ($frontendNeedsBuild) {
    Write-Step "前端代码有变化，正在构建一次性演示页面"
    $env:VITE_API_BASE_URL = $apiBaseUrl
    $env:VITE_USE_MOCK_API = "false"
    Push-Location $frontendDir
    try {
        & $npm run build
        if ($LASTEXITCODE -ne 0) { throw "前端构建失败（退出码 $LASTEXITCODE）。" }
    } finally { Pop-Location }
    [pscustomobject]@{ apiBaseUrl = $apiBaseUrl; builtAtUtc = [DateTime]::UtcNow.ToString("o") } |
        ConvertTo-Json | Set-Content -LiteralPath $FrontendBuildState -Encoding UTF8
} else {
    Write-Step "复用已构建的前端演示页面"
}

$startedRecords = @()
try {
    Write-Step "启动 AI 服务"
    $env:AI_HOST = "127.0.0.1"
    $env:AI_PORT = "$AiPort"
    $aiProcess = Start-Process -FilePath $python -ArgumentList (Join-Path $Root "代码文件\ai-service\app.py") `
        -WorkingDirectory (Join-Path $Root "代码文件\ai-service") -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $Logs "ai.out.log") -RedirectStandardError (Join-Path $Logs "ai.err.log")
    $aiRecord = Get-TrackedProcessRecord -ProcessId $aiProcess.Id -Service "AI"
    $startedRecords += $aiRecord
    Wait-Http "http://127.0.0.1:$AiPort/health" 45 $aiRecord

    Write-Step "启动后端服务"
    $env:SERVER_PORT = "$BackendPort"
    $env:MONGODB_URI = "mongodb://127.0.0.1:27017/$MongoDatabase"
    $env:AI_MODE = "remote"
    $env:AI_BASE_URL = "http://127.0.0.1:$AiPort"
    $env:FRONTEND_ORIGIN = "http://localhost:$FrontendPort"
    $env:FRONTEND_ORIGIN_ALT = "http://127.0.0.1:$FrontendPort"
    $env:JWT_SECRET = $jwtSecret
    $env:DEMO_USER_ENABLED = if ($EnableDemoUser) { "true" } else { "false" }
    $env:DEMO_USERNAME = $DemoUsername
    $env:DEMO_PASSWORD = $DemoPassword
    $backendProcess = Start-Process -FilePath $java -ArgumentList @("-jar", $backendJar) `
        -WorkingDirectory $backendDir -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $Logs "backend.out.log") -RedirectStandardError (Join-Path $Logs "backend.err.log")
    $backendRecord = Get-TrackedProcessRecord -ProcessId $backendProcess.Id -Service "后端"
    $startedRecords += $backendRecord
    Wait-Http "http://127.0.0.1:$BackendPort/actuator/health" 90 $backendRecord

    if ($EnableDemoUser) {
        Write-Step "验证固定演示账号"
        $loginBody = @{ username = $DemoUsername; password = $DemoPassword } | ConvertTo-Json
        try {
            $loginResult = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:$BackendPort/api/v1/auth/login" `
                -ContentType "application/json" -Body $loginBody -TimeoutSec 10
            if ([string]::IsNullOrWhiteSpace([string]$loginResult.token)) { throw "登录响应中缺少令牌。" }
        } catch {
            throw "固定演示账号验证失败。若数据库中已存在同名但密码不同的 demo 用户，请更换演示数据库。原始错误：$($_.Exception.Message)"
        }
    }

    Write-Step "启动前端演示页面"
    $frontendProcess = Start-Process -FilePath $node -ArgumentList @($viteCli, "preview", "--host", "127.0.0.1", "--port", "$FrontendPort", "--strictPort") `
        -WorkingDirectory $frontendDir -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $Logs "frontend.out.log") -RedirectStandardError (Join-Path $Logs "frontend.err.log")
    $frontendRecord = Get-TrackedProcessRecord -ProcessId $frontendProcess.Id -Service "前端"
    $startedRecords += $frontendRecord
    Wait-Http "http://127.0.0.1:$FrontendPort/" 45 $frontendRecord

    $state = [pscustomobject]@{
        schemaVersion = 2
        root = $Root
        startedAtUtc = [DateTime]::UtcNow.ToString("o")
        mongoDatabase = $MongoDatabase
        ports = [pscustomobject]@{ ai = $AiPort; backend = $BackendPort; frontend = $FrontendPort }
        demoUserEnabled = [bool]$EnableDemoUser
        demoUsername = if ($EnableDemoUser) { $DemoUsername } else { $null }
        processes = [pscustomobject]@{ ai = $aiRecord; backend = $backendRecord; frontend = $frontendRecord }
    }
    $state | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $PidFile -Encoding UTF8
} catch {
    for ($index = $startedRecords.Count - 1; $index -ge 0; $index--) {
        Stop-TrackedProcess $startedRecords[$index] | Out-Null
    }
    Remove-Item -LiteralPath $PidFile -Force -ErrorAction SilentlyContinue
    [Console]::Error.WriteLine("启动失败：$($_.Exception.Message)")
    [Console]::Error.WriteLine("日志目录：$Logs")
    exit 1
}

$url = "http://127.0.0.1:$FrontendPort/"
Write-Host ""
Write-Host "全链路已就绪：$url" -ForegroundColor Green
if ($EnableDemoUser) {
    Write-Host "演示账号：$DemoUsername" -ForegroundColor Yellow
    Write-Host "演示密码：$DemoPassword" -ForegroundColor Yellow
}
Write-Host "日志目录：$Logs"
if ($OpenBrowser) {
    Write-Step "打开默认浏览器"
    Start-Process $url
}
