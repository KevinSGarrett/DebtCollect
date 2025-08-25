param(
  [string]$PythonExe = ".venv\Scripts\python.exe"
)
if (-not (Test-Path $PythonExe)) {
  Write-Host "Creating venv..." -ForegroundColor Cyan
  python -m venv .venv
  & ".venv\Scripts\python.exe" -m pip install -U pip
}
Write-Host "Installing requirements..." -ForegroundColor Cyan
& $PythonExe -m pip install -r requirements.txt

Write-Host "Ruff (lint+fix)..." -ForegroundColor Cyan
& $PythonExe -m ruff check . --fix
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host "MyPy..." -ForegroundColor Cyan
& $PythonExe -m mypy .
if ($LASTEXITCODE -ne 0) { exit 1 }

Write-Host "Pytest + coverage..." -ForegroundColor Cyan
& $PythonExe -m pytest -q --maxfail=1 --disable-warnings `
  --cov=. --cov-config=.coveragerc `
  --cov-report=term-missing `
  --cov-report=xml
if ($LASTEXITCODE -ne 0) { exit 1 }

# === Robust coverage XML parsing ===
[xml]$cov = Get-Content "coverage.xml"
$root = $cov.coverage

# Try direct line-rate first
$lineRateStr = $null
try { $lineRateStr = $root.GetAttribute("line-rate") } catch {}

if ([string]::IsNullOrWhiteSpace($lineRateStr)) {
  # Fallback: compute from lines-covered / lines-valid on root
  $linesCoveredStr = $null
  $linesValidStr = $null
  try {
    $linesCoveredStr = $root.GetAttribute("lines-covered")
    $linesValidStr   = $root.GetAttribute("lines-valid")
  } catch {}

  if (-not [string]::IsNullOrWhiteSpace($linesCoveredStr) -and -not [string]::IsNullOrWhiteSpace($linesValidStr)) {
    $covered = [double]$linesCoveredStr
    $valid   = [double]$linesValidStr
    $percent = if ($valid -gt 0) { [Math]::Round(($covered / $valid) * 100, 2) } else { 0 }
  } else {
    # Last resort: sum class-level stats
    $covered = 0.0
    $valid = 0.0
    foreach ($cls in $cov.SelectNodes("//class")) {
      $c = [double]$cls.GetAttribute("lines-covered")
      $v = [double]$cls.GetAttribute("lines-valid")
      $covered += $c
      $valid   += $v
    }
    $percent = if ($valid -gt 0) { [Math]::Round(($covered / $valid) * 100, 2) } else { 0 }
  }
} else {
  $percent = [Math]::Round(([double]$lineRateStr) * 100, 2)
}

Write-Host ("Coverage: {0}%" -f $percent) -ForegroundColor Green
if ($percent -lt 85) {
  Write-Host "Coverage below 85%" -ForegroundColor Red
  exit 1
}

Write-Host "QUALITY GATE PASSED ✅" -ForegroundColor Green
