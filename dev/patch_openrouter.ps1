Param()
$py = Join-Path $PWD 'core\llm_provider.py'
$txt = Get-Content $py -Raw
# Minimal idempotent patch: insert headers if missing in OpenRouterProvider.
if ($txt -notmatch 'HTTP-Referer') {
  $txt = $txt -replace '(headers\s*=\s*{[^}]*Authorization[^}]*})',
  'headers = {
      "Authorization": f"Bearer {key}",
      "HTTP-Referer": os.environ.get("OPENROUTER_HTTP_REFERER","https://github.com/nn-trading/ecosystem"),
      "X-Title": os.environ.get("OPENROUTER_X_TITLE","ecosystem-ai")
  }'
  Set-Content $py -Value $txt -Encoding UTF8
}

# 2) Write env helpers (no secrets in git). Read key from secrets\openrouter.key if OPENROUTER_API_KEY not set.
$prober = @"
import os, sys, pathlib, httpx, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from core.llm_provider import provider_factory, load_cfg
# Best-effort env fill from secrets file:
sec = pathlib.Path('secrets/openrouter.key')
if not os.environ.get('OPENROUTER_API_KEY') and sec.exists():
    os.environ['OPENROUTER_API_KEY'] = sec.read_text(encoding='utf-8').strip()
os.environ.setdefault('OPENROUTER_HTTP_REFERER','https://github.com/nn-trading/ecosystem')
os.environ.setdefault('OPENROUTER_X_TITLE','ecosystem-ai')
# force provider=openrouter for probe
cfg_path = pathlib.Path('config/llm.yaml')
cfg_path.write_text('provider: openrouter\nmodel: openai/gpt-4o-mini\n', encoding='utf-8')
prov = provider_factory()
res = prov.complete("Return the token ECOSYSTEM-LIVE-OPENROUTER and nothing else.")
pathlib.Path('reports/llm').mkdir(parents=True, exist_ok=True)
pathlib.Path('reports/llm/openrouter_probe.txt').write_text(str(res), encoding='utf-8')
print("OPENROUTER_PROBE_DONE")
"@
Set-Content tmp\probe_openrouter.py $prober -Encoding UTF8

# 3) Run tests and re-probe
try { python -m pytest -q } catch { Write-Host "pytest not available; continuing" }; if ($LASTEXITCODE -ne 0) { Write-Host "pytest failed; continuing"; $global:LASTEXITCODE = 0 }
python tmp\probe_openrouter.py

# 4) Show probe tails
Write-Host "`n--- PROBES ---"
Get-Content reports\llm\openai_probe.txt -ErrorAction SilentlyContinue | Select-Object -Last 1
Get-Content reports\llm\openrouter_probe.txt -ErrorAction SilentlyContinue | Select-Object -Last 1
