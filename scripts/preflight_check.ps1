cd C:\Users\nelt2\yamen_academy
Write-Host "PREFLIGHT CHECK" -ForegroundColor Cyan
$procs = Get-Process python,py,pythonw -ErrorAction SilentlyContinue
if ($procs) { $procs | Stop-Process -Force; Start-Sleep -Seconds 2 }
Write-Host "[1] OK no Python running" -ForegroundColor Green
$files = @("app.py","config.py","routes\reading_exam.py","templates\reading\exam_screen.html","templates\reading\result.html","templates\admin.html")
foreach ($f in $files) { if (-not (Test-Path $f)) { Write-Host "MISSING: $f" -ForegroundColor Red; exit 1 } }
Write-Host "[2] OK all critical files exist" -ForegroundColor Green
if (-not (Test-Path "C:\app\data\academy.db")) { Write-Host "MISSING DB" -ForegroundColor Red; exit 1 }
Write-Host "[3] OK DB exists" -ForegroundColor Green
py -m py_compile app.py routes\reading_exam.py
if ($LASTEXITCODE -ne 0) { Write-Host "SYNTAX ERROR" -ForegroundColor Red; exit 1 }
Write-Host "[4] OK syntax check passed" -ForegroundColor Green
$exam = Get-Content "templates\reading\exam_screen.html" -Raw
if ($exam -notmatch "updateArabicTranslation") { Write-Host "MISSING updateArabicTranslation" -ForegroundColor Red; exit 1 }
if ($exam -notmatch "IS_FRESH_ATTEMPT") { Write-Host "MISSING IS_FRESH_ATTEMPT" -ForegroundColor Red; exit 1 }
Write-Host "[5] OK exam_screen.html has all keywords" -ForegroundColor Green
Write-Host "PREFLIGHT OK - run: py app.py" -ForegroundColor Green
