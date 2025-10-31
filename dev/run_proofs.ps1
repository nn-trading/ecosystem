param(
  [int]$STOP_AFTER_SEC = 5
)
$ErrorActionPreference = "SilentlyContinue"
# Ensure proofs and autoacquire are enabled for child process
[System.Environment]::SetEnvironmentVariable("AGENT_DANGER_MODE","1","Process")
[System.Environment]::SetEnvironmentVariable("OMEGA_PROOFS","1","Process")
[System.Environment]::SetEnvironmentVariable("TOOLS_PROOF","1","Process")
[System.Environment]::SetEnvironmentVariable("ECOSYS_HEADLESS","1","Process")
# Forward to standard headless starter with short runtime
& "$PSScriptRoot/start_headless.ps1" -STOP_AFTER_SEC $STOP_AFTER_SEC -HEARTBEAT_SEC 1 -HEALTH_SEC 2
