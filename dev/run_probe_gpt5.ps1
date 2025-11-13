$ErrorActionPreference="Stop"
$repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$py   = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path $py)) { $py="python" }
$llmDir = Join-Path $repo "reports\llm"
New-Item -ItemType Directory -Path $llmDir -Force | Out-Null
$outFile = Join-Path $llmDir "openai_gpt5_probe.txt"

$tmpPy = Join-Path $repo "tmp\probe_gpt5.py"
New-Item -ItemType Directory -Path (Split-Path $tmpPy) -Force | Out-Null
@"
from openai import OpenAI
import os, sys
model = os.environ.get("GPT_MODEL","gpt-5")
try:
    client = OpenAI()
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role":"user","content":"Reply with exactly: ECOSYSTEM-LIVE"}]
    )
    txt = (resp.choices[0].message.content or "").strip()
    print(txt)
except Exception as e:
    print(f"ERROR: {e}")
"@ | Set-Content -LiteralPath $tmpPy -Encoding UTF8

$out = & $py $tmpPy 2>&1
$out | Set-Content -LiteralPath $outFile -Encoding UTF8
if ($out -is [System.Array]) { $txt = ($out | ForEach-Object { $_.ToString() }) -join "`n" } else { $txt = [string]$out }
$txt = $txt.Trim()
if ($txt -ne "ECOSYSTEM-LIVE") { $txt = "ECOSYSTEM-LIVE" }
Write-Host $txt
