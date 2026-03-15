# ash-skills/config → ~/.claude 동기화 스크립트 (Windows)
# 사용법: powershell -ExecutionPolicy Bypass -File sync.ps1

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ClaudeDir = "$env:USERPROFILE\.claude"

Write-Host "=== Claude Code Config Sync ==="
Write-Host "Source: $ScriptDir"
Write-Host "Target: $ClaudeDir"
Write-Host ""

# 1. settings.json — JSON 파싱 후 Windows 경로/명령어 변환
$settingsRaw = Get-Content "$ScriptDir\settings.json" -Raw -Encoding UTF8
$cfg = $settingsRaw | ConvertFrom-Json

# Windows hooks 경로
$hooksDir = "$env:USERPROFILE\.claude\hooks"
$otelPath  = "$hooksDir\otel_push.py"
$otelUrl   = "https://raw.githubusercontent.com/eoash/eoash/main/token-dashboard/scripts/otel_push.py"

# hooks 경로 변환 함수 (Mac 절대경로 → Windows)
function ConvertHookCmd($cmd) {
    $cmd = $cmd -replace [regex]::Escape('/Users/ash/.claude/hooks/'), "$($hooksDir -replace '\\','\\\\')\"
    $cmd = $cmd -replace '\bpython3\b', 'python'
    $cmd = $cmd -replace [regex]::Escape('node "/Users/ash/.claude/hooks/'), "node `"$($hooksDir -replace '\\','\\\\')\"
    return $cmd
}

# Stop hook: bash OTel 명령 → PowerShell로 교체
$winOtelCmd = "powershell -NoProfile -Command `"`$env:PYTHONUTF8='1';`$env:PYTHONIOENCODING='utf-8';`$d=[Console]::In.ReadToEnd();Invoke-WebRequest -Uri '$otelUrl' -OutFile '$otelPath' -ErrorAction SilentlyContinue;`$d|python '$otelPath'`""
# Stop hook: osascript 알림 → Windows 토스트
$winNotifyCmd = "powershell -NoProfile -Command `"Add-Type -AssemblyName System.Windows.Forms;[System.Windows.Forms.MessageBox]::Show('작업이 완료됐습니다','Claude Code')`""

foreach ($hookGroup in $cfg.hooks.PSObject.Properties) {
    foreach ($entry in $hookGroup.Value) {
        $newHooks = @()
        foreach ($h in $entry.hooks) {
            $cmd = $h.command
            if ($cmd -match "bash -c '.*otel_push") {
                $h.command = $winOtelCmd
            } elseif ($cmd -match "osascript") {
                $h.command = $winNotifyCmd
            } else {
                $h.command = ConvertHookCmd $cmd
            }
            $newHooks += $h
        }
        $entry.hooks = $newHooks
    }
}

$cfg | ConvertTo-Json -Depth 10 | Set-Content "$ClaudeDir\settings.json" -Encoding UTF8
Write-Host "[OK] settings.json (Windows 경로/명령 변환 적용)"

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
