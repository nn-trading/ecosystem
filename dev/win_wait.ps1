param(
  [Parameter(Mandatory=$true)][string]$Substring,
  [int]$TimeoutSec = 15,
  [int]$PollMs = 200
)
$ErrorActionPreference = 'Stop'
$sw = [System.Diagnostics.Stopwatch]::StartNew()

function Get-ActiveTitle {
  try {
    if (-not ([System.Management.Automation.PSTypeName]'Win32.WinAPI').Type) {
      $sig = @"
using System;
using System.Runtime.InteropServices;
using System.Text;
public static class WinAPI {
  [DllImport("user32.dll")]
  public static extern IntPtr GetForegroundWindow();

  [DllImport("user32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
  public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
}
"@;
      Add-Type -TypeDefinition $sig -Language CSharp -Namespace 'Win32' -Name 'WinAPI' -ErrorAction Stop | Out-Null
    }
    $h = [Win32.WinAPI]::GetForegroundWindow()
    $buf = New-Object System.Text.StringBuilder 512
    [void][Win32.WinAPI]::GetWindowText($h, $buf, 512)
    return $buf.ToString()
  } catch {
    try {
      $p = Get-Process | Where-Object { $_.MainWindowHandle -ne 0 } | Sort-Object StartTime -Descending | Select-Object -First 1
      return $p.MainWindowTitle
    } catch { return '' }
  }
}

$deadline = (Get-Date).AddSeconds($TimeoutSec)
while ((Get-Date) -lt $deadline) {
  $t = Get-ActiveTitle
  if ($t -and ($t -like ('*' + $Substring + '*'))) {
    $out = @{ ok = $true; title = $t; contains = $Substring; waited_ms = $sw.ElapsedMilliseconds }
    $sw.Stop(); $out | ConvertTo-Json -Compress; exit 0
  }
  Start-Sleep -Milliseconds $PollMs
}
$out = @{ ok = $false; title = (Get-ActiveTitle); contains = $Substring; timeout_sec = $TimeoutSec }
$sw.Stop(); $out | ConvertTo-Json -Compress; exit 1
