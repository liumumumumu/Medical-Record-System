$ErrorActionPreference = "Stop"
$Root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$PidFile = Join-Path $Root ".runtime\pids.json"

. (Join-Path $PSScriptRoot "runtime-process.ps1")

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

if (-not (Test-Path -LiteralPath $PidFile)) {
    Write-Host "没有由本项目启动器启动的服务。"
    exit 0
}

try {
    $state = Get-Content -Raw -LiteralPath $PidFile | ConvertFrom-Json
} catch {
    [Console]::Error.WriteLine("关闭失败：启动记录损坏。为避免误关其他程序，本次没有结束任何进程。")
    exit 2
}

if ([int]$state.schemaVersion -ne 2 -or $null -eq $state.processes) {
    [Console]::Error.WriteLine("关闭失败：这是旧版启动记录。为避免 PID 复用导致误关程序，本次没有结束任何进程。")
    exit 2
}

if (-not [String]::Equals([IO.Path]::GetFullPath([string]$state.root), $Root, [StringComparison]::OrdinalIgnoreCase)) {
    [Console]::Error.WriteLine("关闭失败：启动记录属于另一个项目目录，本次没有结束任何进程。")
    exit 2
}

Write-Host "正在安全关闭前端、后端和 AI 服务……" -ForegroundColor Cyan
$identityMismatches = @()
foreach ($record in @($state.processes.frontend, $state.processes.backend, $state.processes.ai)) {
    if ($null -eq $record) { continue }
    $result = Stop-TrackedProcess $record
    switch ($result) {
        "Stopped" { Write-Host "已关闭：$($record.service)" }
        "AlreadyStopped" { Write-Host "已停止：$($record.service)" }
        "IdentityMismatch" {
            $identityMismatches += $record.service
            Write-Warning "$($record.service) 的 PID 已属于其他程序，已安全跳过。"
        }
    }
}

Remove-Item -LiteralPath $PidFile -Force

$ports = @([int]$state.ports.ai, [int]$state.ports.backend, [int]$state.ports.frontend)
$deadline = [DateTime]::UtcNow.AddSeconds(10)
while ([DateTime]::UtcNow -lt $deadline) {
    $busy = @($ports | Where-Object { Test-Port $_ })
    if ($busy.Count -eq 0) { break }
    Start-Sleep -Milliseconds 250
}

$remaining = @($ports | Where-Object { Test-Port $_ })
if ($remaining.Count -gt 0) {
    foreach ($port in $remaining) {
        [Console]::Error.WriteLine("端口 $port 仍被 $(Get-PortOwnerDescription $port) 占用；为避免误关，启动器没有强制结束该进程。")
    }
    exit 2
}

Write-Host "本项目服务已全部关闭；MongoDB 系统服务保持运行。" -ForegroundColor Green
if ($identityMismatches.Count -gt 0) {
    Write-Host "检测到陈旧 PID，但均已安全跳过，没有触碰其他程序。" -ForegroundColor Yellow
}
