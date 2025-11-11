param()
# NOOP scrubber used by tree-filter; always succeed
try {
  Write-Host 'NOOP: dev/_treefilter_scrub.ps1 invoked' -ForegroundColor DarkGray
  exit 0
} catch { exit 0 }
