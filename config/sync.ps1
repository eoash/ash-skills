# ash-skills/config → ~/.claude 동기화 스크립트 (Windows)
# 사용법: powershell -ExecutionPolicy Bypass -File sync.ps1

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ClaudeDir = "$env:USERPROFILE\.claude"

Write-Host "=== Claude Code Config Sync ==="
Write-Host "Source: $ScriptDir"
Write-Host "Target: $ClaudeDir"
Write-Host ""

# 1. settings.json — 경로를 Windows 형식으로 치환
$settings = Get-Content "$ScriptDir\settings.json" -Raw -Encoding UTF8
# Mac 경로 → Windows 경로 변환
$settings = $settings -replace '/Users/ash/', "$($env:USERPROFILE -replace '\\','/')/"
$settings = $settings -replace 'python3', 'python'
$settings = $settings -replace 'osascript.*?"', 'powershell -Command \"[System.Media.SystemSounds]::Asterisk.Play(); [System.Windows.Forms.MessageBox]::Show(''작업이 완료됐습니다'',''Claude Code'')\"'
Set-Content "$ClaudeDir\settings.json" $settings -Encoding UTF8
Write-Host "[OK] settings.json (경로 변환 적용)"

# 2. hooks
New-Item -ItemType Directory -Force -Path "$ClaudeDir\hooks" | Out-Null
Copy-Item "$ScriptDir\hooks\*" "$ClaudeDir\hooks\" -Force
$hookCount = (Get-ChildItem "$ScriptDir\hooks\").Count
Write-Host "[OK] hooks ($hookCount 개 파일)"

# 3. memory
$memoryDir = $null
Get-ChildItem "$ClaudeDir\projects\" -Directory | Where-Object { $_.Name -match "eoash" } | ForEach-Object {
    $memoryDir = "$($_.FullName)\memory"
}

if ($memoryDir) {
    New-Item -ItemType Directory -Force -Path $memoryDir | Out-Null
    Copy-Item "$ScriptDir\memory\*" "$memoryDir\" -Force
    $memCount = (Get-ChildItem "$ScriptDir\memory\").Count
    Write-Host "[OK] memory -> $memoryDir ($memCount 개 파일)"
} else {
    Write-Host "[SKIP] eoash 프로젝트 메모리 디렉토리를 찾을 수 없음"
    Write-Host "       Claude Code에서 eoash 프로젝트를 한 번 열어야 디렉토리가 생성됩니다."
}

Write-Host ""
Write-Host "=== 동기화 완료 ==="
