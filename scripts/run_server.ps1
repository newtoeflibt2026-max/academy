# تشغيل الخادم مع فحص قبلي تلقائي
& "$PSScriptRoot\preflight_check.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ فشل preflight — توقف" -ForegroundColor Red
    exit 1
}
Write-Host "🚀 بدء الخادم..." -ForegroundColor Cyan
py app.py
