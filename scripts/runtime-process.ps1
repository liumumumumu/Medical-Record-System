function Get-ProcessCreationTimeUtc {
    param([Parameter(Mandatory = $true)]$CimProcess)

    $value = $CimProcess.CreationDate
    if ($null -eq $value) { return "" }
    if ($value -is [DateTime]) {
        return $value.ToUniversalTime().ToString("o", [Globalization.CultureInfo]::InvariantCulture)
    }

    try {
        $date = [Management.ManagementDateTimeConverter]::ToDateTime([string]$value)
        return $date.ToUniversalTime().ToString("o", [Globalization.CultureInfo]::InvariantCulture)
    } catch {
        return [string]$value
    }
}

function Get-TrackedProcessRecord {
    param(
        [Parameter(Mandatory = $true)][int]$ProcessId,
        [Parameter(Mandatory = $true)][string]$Service
    )

    $process = $null
    for ($attempt = 0; $attempt -lt 20 -and $null -eq $process; $attempt++) {
        $process = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction SilentlyContinue
        if ($null -eq $process) { Start-Sleep -Milliseconds 100 }
    }
    if ($null -eq $process) { throw "$Service 进程启动后立即退出（PID $ProcessId）。" }

    return [pscustomobject]@{
        service = $Service
        pid = [int]$process.ProcessId
        name = [string]$process.Name
        creationTimeUtc = Get-ProcessCreationTimeUtc $process
        executablePath = [string]$process.ExecutablePath
        commandLine = [string]$process.CommandLine
    }
}

function Test-TrackedProcessIdentity {
    param([Parameter(Mandatory = $true)]$Record)

    if ($null -eq $Record.pid -or $null -eq $Record.creationTimeUtc -or $null -eq $Record.commandLine) {
        return $false
    }

    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$([int]$Record.pid)" -ErrorAction SilentlyContinue
    if ($null -eq $process) { return $false }

    $sameCreationTime = [String]::Equals(
        (Get-ProcessCreationTimeUtc $process),
        [string]$Record.creationTimeUtc,
        [StringComparison]::Ordinal
    )
    $sameName = [String]::Equals([string]$process.Name, [string]$Record.name, [StringComparison]::OrdinalIgnoreCase)
    $sameExecutable = [String]::Equals(
        [string]$process.ExecutablePath,
        [string]$Record.executablePath,
        [StringComparison]::OrdinalIgnoreCase
    )
    $sameCommandLine = [String]::Equals(
        [string]$process.CommandLine,
        [string]$Record.commandLine,
        [StringComparison]::Ordinal
    )

    return $sameCreationTime -and $sameName -and $sameExecutable -and $sameCommandLine
}

function Stop-ProcessTreeById {
    param([Parameter(Mandatory = $true)][int]$ProcessId)

    $children = Get-CimInstance Win32_Process -Filter "ParentProcessId=$ProcessId" -ErrorAction SilentlyContinue
    foreach ($child in $children) {
        Stop-ProcessTreeById -ProcessId ([int]$child.ProcessId)
    }
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
}

function Stop-TrackedProcess {
    param([Parameter(Mandatory = $true)]$Record)

    $process = Get-CimInstance Win32_Process -Filter "ProcessId=$([int]$Record.pid)" -ErrorAction SilentlyContinue
    if ($null -eq $process) { return "AlreadyStopped" }
    if (-not (Test-TrackedProcessIdentity $Record)) { return "IdentityMismatch" }

    Stop-ProcessTreeById -ProcessId ([int]$Record.pid)
    return "Stopped"
}
