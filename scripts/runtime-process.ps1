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
        $process = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
        if ($null -eq $process) { Start-Sleep -Milliseconds 100 }
    }
    if ($null -eq $process) { throw "$Service 进程启动后立即退出（PID $ProcessId）。" }

    $creationTimeUtc = ""
    $executablePath = ""
    try { $creationTimeUtc = $process.StartTime.ToUniversalTime().ToString("o", [Globalization.CultureInfo]::InvariantCulture) } catch {}
    try { $executablePath = [string]$process.Path } catch {}

    return [pscustomobject]@{
        service = $Service
        pid = [int]$process.Id
        name = [string]$process.ProcessName
        creationTimeUtc = $creationTimeUtc
        executablePath = $executablePath
        commandLine = ""
    }
}

function Test-TrackedProcessIdentity {
    param([Parameter(Mandatory = $true)]$Record)

    if ($null -eq $Record.pid -or [string]::IsNullOrWhiteSpace([string]$Record.creationTimeUtc)) {
        return $false
    }

    $process = Get-Process -Id ([int]$Record.pid) -ErrorAction SilentlyContinue
    if ($null -eq $process) { return $false }

    $creationTimeUtc = ""
    $executablePath = ""
    try { $creationTimeUtc = $process.StartTime.ToUniversalTime().ToString("o", [Globalization.CultureInfo]::InvariantCulture) } catch { return $false }
    try { $executablePath = [string]$process.Path } catch {}

    $sameCreationTime = [String]::Equals(
        $creationTimeUtc,
        [string]$Record.creationTimeUtc,
        [StringComparison]::Ordinal
    )
    $sameName = [String]::Equals([string]$process.ProcessName, [string]$Record.name, [StringComparison]::OrdinalIgnoreCase)
    $sameExecutable = [string]::IsNullOrWhiteSpace([string]$Record.executablePath) -or
        [string]::IsNullOrWhiteSpace($executablePath) -or
        [String]::Equals($executablePath, [string]$Record.executablePath, [StringComparison]::OrdinalIgnoreCase)

    return $sameCreationTime -and $sameName -and $sameExecutable
}

function Stop-ProcessTreeById {
    param([Parameter(Mandatory = $true)][int]$ProcessId)

    # The launcher records the actual Python, Java and Node server PIDs, so they
    # can be stopped directly.  Do not enumerate a process tree here: both the
    # CIM provider and taskkill /T are unreliable on some Windows installations.
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue

    for ($attempt = 0; $attempt -lt 20; $attempt++) {
        if ($null -eq (Get-Process -Id $ProcessId -ErrorAction SilentlyContinue)) { return }
        Start-Sleep -Milliseconds 100
    }

    throw "进程树未能及时关闭（PID $ProcessId）。"
}

function Stop-TrackedProcess {
    param([Parameter(Mandatory = $true)]$Record)

    $process = Get-Process -Id ([int]$Record.pid) -ErrorAction SilentlyContinue
    if ($null -eq $process) { return "AlreadyStopped" }
    if (-not (Test-TrackedProcessIdentity $Record)) { return "IdentityMismatch" }

    Stop-ProcessTreeById -ProcessId ([int]$Record.pid)
    return "Stopped"
}
