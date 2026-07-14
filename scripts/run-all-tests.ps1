$ErrorActionPreference = "Stop"
$Root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$env:JWT_SECRET = "test-only-secret-2026-test-only-secret-2026-test-only-secret"

function Invoke-Checked([scriptblock]$Command, [string]$Label) {
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Label 失败，退出码：$LASTEXITCODE"
    }
}

Push-Location (Join-Path $Root "代码文件\ai-service")
try { Invoke-Checked { python -m pytest -p no:cacheprovider -q } "AI 服务测试" } finally { Pop-Location }

Push-Location (Join-Path $Root "代码文件\data-analysis")
try {
    Invoke-Checked { python -m pytest -p no:cacheprovider -q } "数据模块测试"
    Invoke-Checked { python scripts\preprocess.py } "病例预处理"
    Invoke-Checked { python scripts\feature_builder.py } "特征构建"
    Invoke-Checked { python scripts\run_pipeline.py } "NHANES 流水线"
} finally { Pop-Location }

Push-Location (Join-Path $Root "代码文件\backend-service")
try { Invoke-Checked { .\mvnw.cmd test } "后端测试" } finally { Pop-Location }

Push-Location (Join-Path $Root "代码文件\frontend\frontend")
try {
    Invoke-Checked { npm test } "前端测试"
    Invoke-Checked { npm run build } "前端构建"
} finally { Pop-Location }

Write-Host "所有模块测试、构建和数据流水线均已通过。"
