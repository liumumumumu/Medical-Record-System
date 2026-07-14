param([string]$Output = "医疗病历生成与分析系统-delivery.zip")

$ErrorActionPreference = "Stop"
$Root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$Target = [IO.Path]::GetFullPath((Join-Path $Root $Output))
$RootPrefix = $Root.TrimEnd('\') + '\'
if (-not $Target.StartsWith($RootPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw "输出文件必须位于项目目录内。"
}

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
if (Test-Path -LiteralPath $Target) { Remove-Item -LiteralPath $Target -Force }
$archive = [IO.Compression.ZipFile]::Open($Target, [IO.Compression.ZipArchiveMode]::Create)
try {
    $excludedNames = @(
        '.git', '.runtime', '.agents', '.idea', '.vscode', '.venv',
        'dataset', 'node_modules', 'dist', 'target', 'tmp', 'venv',
        '__pycache__', '.pytest_cache'
    )

    function Test-ExcludedDirectory([string]$RelativePath, [string]$Name) {
        if ($excludedNames -contains $Name) { return $true }
        return $RelativePath -match '(^|\\)data\\(uploads|reports|mongodb|logs)(\\|$)'
    }

    function Add-DirectoryToArchive([string]$Directory) {
        foreach ($item in Get-ChildItem -LiteralPath $Directory -Force -ErrorAction Stop) {
            $relative = $item.FullName.Substring($Root.Length).TrimStart('\')
            if ($item.PSIsContainer) {
                if (-not (Test-ExcludedDirectory $relative $item.Name)) {
                    Add-DirectoryToArchive $item.FullName
                }
                continue
            }
            if ($item.FullName -eq $Target -or
                $item.Name -in @('AGENTS.md', 'handoff-pending.md') -or
                $item.Name -match '\.(pyc|tsbuildinfo)$' -or
                ($item.Name -like '.env*' -and $item.Name -ne '.env.example')) { continue }
            $entryName = $relative.Replace('\', '/')
            [IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                $archive, $item.FullName, $entryName, [IO.Compression.CompressionLevel]::Optimal) | Out-Null
        }
    }

    Add-DirectoryToArchive $Root
} finally {
    $archive.Dispose()
}
Write-Host "已生成：$Target"
