$ErrorActionPreference = "Stop"
$py   = "C:\bots\ecosys\.venv\Scripts\python.exe"
$img  = "C:\bots\ecosys\reports\screens\ocr_smoke.png"
$out  = "C:\bots\ecosys\reports\proofs\ocr_smoke.txt"

# Ensure directories exist
$imgDir = Split-Path $img -Parent
$outDir = Split-Path $out -Parent
if (!(Test-Path $imgDir)) { New-Item -ItemType Directory -Force -Path $imgDir | Out-Null }
if (!(Test-Path $outDir)) { New-Item -ItemType Directory -Force -Path $outDir | Out-Null }

# 1) Desktop screenshot
& $py "C:\bots\ecosys\tools\gui_tool.py" screenshot --path $img | Out-Null

# 2) OCR it and save text
$ocrJson = & $py "C:\bots\ecosys\tools\gui_tool.py" ocr --image $img
try { $obj = $ocrJson | ConvertFrom-Json } catch { Write-Host ('OCR parse failed: ' + $ocrJson) -ForegroundColor Red; exit 1 }
Set-Content -Encoding UTF8 -Path $out -Value ($obj.text)

Write-Host ('OK: OCR text saved -> ' + $out) -ForegroundColor Green
