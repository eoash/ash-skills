# OTel Stop Hook — Windows용 wrapper
# Claude Code Stop 이벤트 시 stdin 데이터를 otel_push.py에 전달
# 사용법: settings.json Stop hook에 "powershell -NoProfile -File ...\otel_hook.ps1" 등록

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'

$hooksDir = "$env:USERPROFILE\.claude\hooks"
$otelScript = "$hooksDir\otel_push.py"
$otelUrl = "https://raw.githubusercontent.com/eoash/eoash/main/token-dashboard/scripts/otel_push.py"

# stdin 읽기
$stdinData = [Console]::In.ReadToEnd()

# 최신 otel_push.py 다운로드 (실패해도 계속)
try {
    Invoke-WebRequest -Uri $otelUrl -OutFile $otelScript -ErrorAction SilentlyContinue
} catch {}

# Python에 stdin 전달
$stdinData | python $otelScript
