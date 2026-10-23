$ErrorActionPreference = "Stop"

$ProductRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Workspace = (Resolve-Path (Join-Path $ProductRoot "..\..")).Path
$Recorded = (Get-Content -LiteralPath (Join-Path $Workspace "WORKSPACE.txt") -Raw).Trim()
if ([System.IO.Path]::GetFullPath($Recorded) -ne $Workspace) {
    throw "Refusing: WORKSPACE.txt does not match the resolved workspace."
}

$Python = Join-Path $Workspace ".venvs\organize\Scripts\python.exe"
$MantleSource = Join-Path $Workspace "sources\mantle-os\src"
if (-not (Test-Path -LiteralPath $Python -PathType Leaf)) {
    throw "Organize.AppAI Python environment is missing: $Python"
}
if (-not (Test-Path -LiteralPath (Join-Path $ProductRoot ".mantle\organism.json") -PathType Leaf)) {
    throw "Organize.AppAI resident is missing from $ProductRoot\.mantle"
}

$env:PYTHONPATH = $MantleSource
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"
$env:ORGANIZE_APPAI_WORKSPACE = $Workspace

Set-Location -LiteralPath $Workspace
Clear-Host
& $Python -m organize.mantle_appai.terminal --product-root $ProductRoot --setup-key
