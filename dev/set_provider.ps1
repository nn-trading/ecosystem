param(
  [string]$Provider = "openai",
  [string]$Model    = "gpt-5"
)
$repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$cfgDir = Join-Path $repo "config"
New-Item -ItemType Directory -Path $cfgDir -Force | Out-Null
$cfgPath = Join-Path $cfgDir "llm.yaml"
@"
provider: $Provider
model: $Model
"@ | Set-Content -LiteralPath $cfgPath -Encoding UTF8
Write-Host ("provider_now: " + $Provider)
Write-Host ("model_now: " + $Model)
