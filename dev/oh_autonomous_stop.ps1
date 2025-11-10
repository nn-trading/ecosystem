param()
$ErrorActionPreference='Stop'
$ROOT=(Get-Item (Split-Path -Parent $MyInvocation.MyCommand.Path)).Parent.FullName
$PIDS=Join-Path $ROOT 'reports\AUTONOMOUS_PIDS.json'
try{
  if(Test-Path $PIDS){
    $p=Get-Content $PIDS -Raw | ConvertFrom-Json
    foreach($id in @($p.tool,$p.dispatch,$p.router)){ try{ if($id){ Stop-Process -Id $id -Force -ErrorAction SilentlyContinue } }catch{} }
  }
}catch{}
try{ powershell -NoProfile -File (Join-Path $ROOT 'start.ps1') -Stop 1 | Out-Null }catch{}
Write-Host '=== AUTONOMOUS STACK STOPPED ==='
