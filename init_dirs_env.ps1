foreach($d in 'C:\bots\ecosys','C:\bots\ecosys\dev','C:\bots\ecosys\tools','C:\bots\ecosys\reports','C:\bots\ecosys\reports\screens','C:\bots\ecosys\secrets'){
    if(-not (Test-Path $d)){
        New-Item -ItemType Directory -Force -Path $d | Out-Null
    }
}
setx PYTHONUTF8 1 | Out-Null
setx PYTHONIOENCODING utf-8 | Out-Null
setx AGENT_DANGER_MODE 1 | Out-Null
