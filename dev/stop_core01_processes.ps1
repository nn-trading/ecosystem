Param(
    [string]$FixPids = "reports\CORE01_FIX_PIDS.json",
    [string]$ForcePids = "reports\CORE01_FORCE_TAIL_PIDS.json",
    [switch]$DryRun
)

$stopped = @()
$errors = @()

function TryStopPid {
    param([int]$Pid, [string]$Label)
    if (-not $Pid) { return }
    try {
        $p = Get-Process -Id $Pid -ErrorAction Stop
        if ($DryRun) {
            $stopped += "$Label:$Pid (dry)"
        } else {
            Stop-Process -Id $Pid -Force -ErrorAction Stop
            $stopped += "$Label:$Pid"
        }
    } catch {
        $errors += "$Label:$Pid $_"
    }
}

if (Test-Path $FixPids) {
    try {
        $fix = Get-Content $FixPids -Raw | ConvertFrom-Json
        TryStopPid $fix.tool "tool"
        TryStopPid $fix.dispatch "dispatch"
        TryStopPid $fix.router "router"
    } catch {
        $errors += "read:$FixPids $_"
    }
}

if (Test-Path $ForcePids) {
    try {
        $fb = Get-Content $ForcePids -Raw | ConvertFrom-Json
        $rp = $null
        if ($fb.PSObject.Properties.Name -contains "router_pid") { $rp = $fb.router_pid }
        elseif ($fb.PSObject.Properties.Name -contains "router") { $rp = $fb.router }
        if ($rp) { TryStopPid $rp "router_fallback" }
    } catch {
        $errors += "read:$ForcePids $_"
    }
}

$out = @()
$out += "CORE01_STOP " + (Get-Date -Format s)
$out += "dryrun=" + $DryRun.IsPresent
$out += "stopped=" + ($stopped -join ", ")
$out += "errors=" + ($errors -join " | ")
$outText = ($out -join "`r`n") + "`r`n"
Set-Content -Path "reports\CORE01_STOP_SUMMARY.txt" -Value $outText -Encoding Ascii
