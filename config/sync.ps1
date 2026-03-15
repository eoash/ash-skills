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

# hooks 경로 변환 함수 (Mac 절대경로 → Windows 포워드슬래시)
# 포워드슬래시 사용 이유: 백슬래시 → regex replace → ConvertTo-Json 3단계 이스케이핑 버그 회피
# Windows는 Python/Node 경로에서 / 를 \ 와 동일하게 허용함
function ConvertHookCmd($cmd) {
    $fwdHooksDir = $hooksDir -replace '\\', '/'  # C:\...\hooks → C:/.../hooks
    $cmd = $cmd -replace [regex]::Escape('/Users/ash/.claude/hooks'), $fwdHooksDir
    $cmd = $cmd -replace '\bpython3\b', 'python'
    return $cmd
}

# Stop hook: bash OTel → PowerShell -File wrapper (인라인 중첩 방지)
$otelHookPath = "$hooksDir\otel_hook.ps1"
$winOtelCmd = "powershell -NoProfile -ExecutionPolicy Bypass -File `"$otelHookPath`""
# Stop hook: osascript 알림 → Windows 토스트 (별도 .ps1 불필요, 간단한 알림)
$winNotifyCmd = "powershell -NoProfile -Command `"[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms');[System.Windows.Forms.MessageBox]::Show('Done','Claude Code')`""

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

# 3. memory — eoash 레포가 어디 클론됐든 매칭
# 지원 경로: Documents\eoash, ash, 또는 기타 클론 위치
$memoryDir = $null
$repoPatterns = @("eoash", "C--Users-ash-ash", "C--Users-ash-Documents-eoash")
Get-ChildItem "$ClaudeDir\projects\" -Directory | ForEach-Object {
    $name = $_.Name
    foreach ($pattern in $repoPatterns) {
        if ($name -match [regex]::Escape($pattern) -or $name -eq $pattern) {
            $memoryDir = "$($_.FullName)\memory"
            break
        }
    }
}

if ($memoryDir) {
    New-Item -ItemType Directory -Force -Path $memoryDir | Out-Null
    Copy-Item "$ScriptDir\memory\*" "$memoryDir\" -Force
    $memCount = (Get-ChildItem "$ScriptDir\memory\").Count
    Write-Host "[OK] memory -> $memoryDir ($memCount 개 파일)"
} else {
    Write-Host "[SKIP] eoash 프로젝트 메모리 디렉토리를 찾을 수 없음"
    Write-Host "       Claude Code에서 eoash 레포 경로를 한 번 열면 디렉토리가 자동 생성됩니다."
    Write-Host "       지원 패턴: $($repoPatterns -join ', ')"
}

Write-Host ""
Write-Host "=== 동기화 완료 ==="
