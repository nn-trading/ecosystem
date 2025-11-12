param(
  [string]$Model = "llama3.1:8b-instruct"
)
$ErrorActionPreference="Stop"
$repo="C:\bots\ecosys"
Set-Location $repo
$cfg = "config\llm.yaml"
$marker = "ECOSYSTEM-LIVE-OLLAMA"

# Temp switch provider to gpt-oss for the probe (without committing yet)
$yaml = Get-Content $cfg -Raw
$yaml = $yaml -replace "(?m)^provider:.*$", "provider: gpt-oss"
$yaml = $yaml -replace "(?m)^model:.*$",    "model: $Model"
$yaml | Set-Content -Encoding UTF8 $cfg

# Minimal Python check calling provider_factory() so we exercise the real code path
$py = @"
import sys, json
from core.llm_provider import load_cfg, provider_factory
cfg = load_cfg()
prov = provider_factory()
out = prov.complete("return exactly: $marker", system="health check")
print(out.strip())
"@
$tmpPy = Join-Path $repo "tmp\gpt_oss_probe.py"
New-Item -ItemType Directory -Force -Path (Split-Path $tmpPy) | Out-Null
Set-Content -LiteralPath $tmpPy -Value $py -Encoding UTF8

# Run the probe
$venvPy = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) { $venvPy = "python" }
$out = & $venvPy $tmpPy 2>&1
$out = [string]$out
$out | Set-Content -Encoding UTF8 (Join-Path $repo "reports\llm\ollama_probe.txt")

if ($out -match [regex]::Escape($marker)) {
  Write-Host "OLLAMA_OK"
  exit 0
} else {
  Write-Host "OLLAMA_FAIL: $out"
  exit 2
}
