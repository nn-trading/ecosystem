$bundle = (Get-Content -Raw 'logs/conf_bundle_path.out').Trim()
if (-not $bundle) { Write-Error 'Bundle path missing'; exit 1 }
New-Item -ItemType Directory -Force -Path $bundle | Out-Null
Copy-Item 'logs/conf_*.out' "$bundle\" -ErrorAction SilentlyContinue
Copy-Item 'logs/conf_*.json' "$bundle\" -ErrorAction SilentlyContinue
Copy-Item 'reports/snapshot_validate.json' "$bundle\" -ErrorAction SilentlyContinue
