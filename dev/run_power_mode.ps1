$ErrorActionPreference = 'Stop'
Set-Location -Path 'C:\bots'

$ROOT = 'C:\bots\ecosys'
$ts = Get-Date -Format 'yyyyMMdd_HHmmss'
$run = Join-Path $ROOT "runs\$ts"
New-Item -ItemType Directory -Path $run -Force | Out-Null

# Safety checkpoint + kill stragglers
git -C $ROOT diff | Out-File -FilePath "$run\emergency.patch" -Encoding utf8
try { taskkill /f /im python.exe 2>$null | Out-Null } catch {}

# Runtime env
$env:AGENT_DANGER_MODE = '1'
$env:AUTOACQUIRE_MAX = '3'
$env:OMEGA_PROOFS = '1'

$python = Join-Path $ROOT '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { throw "Python not found: $python" }

# Preflight snapshot (bytes-safe) + trigger omega.run if available
@'
import os, sys, json, sqlite3, shutil, glob, subprocess, time, base64
ROOT=r"C:\bots\ecosys"
sys.path.insert(0, ROOT)
ts=time.strftime("%Y%m%d_%H%M%S")
base=os.path.join(ROOT,"runs",ts,"preflight"); os.makedirs(base, exist_ok=True)

def js(v):
    if isinstance(v, bytes): return {"__bytes_b64__": base64.b64encode(v).decode("ascii")}
    if isinstance(v, dict): return {str(k): js(x) for k,x in v.items()}
    if isinstance(v, (list, tuple)): return [js(x) for x in v]
    try: json.dumps(v); return v
    except Exception: return str(v)

# 1) git diff
try:
    p=subprocess.run(["git","-C",ROOT,"diff"],capture_output=True,text=True,encoding="utf-8",timeout=20)
    open(os.path.join(base,"changes.patch"),"w",encoding="utf-8").write(p.stdout or "")
except Exception as e:
    open(os.path.join(base,"changes.patch"),"w",encoding="utf-8").write(f"# git diff failed: {e}\n")

# 2) tools list (best effort)
names_txt=os.path.join(ROOT,"logs","proofs","tools_registry_names.txt")
names=[ln.strip() for ln in open(names_txt,"r",encoding="utf-8",errors="ignore") if ln.strip()] if os.path.exists(names_txt) else []
json.dump({"tools":names}, open(os.path.join(base,"tools_registry_names.json"),"w",encoding="utf-8"), ensure_ascii=True, indent=2)

# 3) copy logs
tasks=os.path.join(ROOT,"logs","tasks.json")
shutil.copy2(tasks, os.path.join(base,"tasks.json")) if os.path.exists(tasks) else None
proofs=os.path.join(ROOT,"logs","proofs")
shutil.copytree(proofs, os.path.join(base,"proofs"), dirs_exist_ok=True) if os.path.isdir(proofs) else None

# 4) sqlite dump (read-only)
db_info={}
cands=[]
for d in ("var","data","assistant"):
    p=os.path.join(ROOT,d)
    if os.path.isdir(p): cands+=glob.glob(os.path.join(p,"**","*.db"),recursive=True)
for db in sorted(set(cands))[:12]:
    try:
        conn=sqlite3.connect(f"file:{db}?mode=ro", uri=True); conn.row_factory=sqlite3.Row; cur=conn.cursor()
        cur.execute("SELECT name, sql FROM sqlite_master WHERE type IN ('table','index','view','trigger')")
        schema=[{"name":r[0],"sql":r[1]} for r in cur.fetchall()]
        sample={}
        for s in schema:
            t=s[0]
            if not t or t=="sqlite_sequence": continue
            try:
                cur.execute(f'PRAGMA table_info("{t}")'); cols=[r[1] for r in cur.fetchall()]
                cur.execute(f'SELECT * FROM "{t}" LIMIT 200');
                cols2=[d[0] for d in cur.description] if cur.description else []
                rows=[{k: js(row[i]) for i,k in enumerate(cols2)} for row in cur.fetchall()]
                sample[t]={"columns":cols2 or cols,"rows":rows}
            except Exception as e: sample[t] = {"error":str(e)}
        db_info[db]={"schema":schema,"sample":sample}; conn.close()
    except Exception as e:
        db_info[db]={"error":str(e)}
json.dump(db_info, open(os.path.join(base,"memory_dump.json"),"w",encoding="utf-8"), ensure_ascii=True)
print("PREFLIGHT_PATH", os.path.abspath(base))

# Trigger omega.run if present
try:
    from core.tools import REGISTRY as TR
    names = list(TR.available())
    print("tools_count", len(names))
    print("omega_in_registry", "omega.run" in names)
    if "omega.run" in names:
        res=TR.call("omega.run")
        try:
            ok = res.get("ok")
        except Exception:
            ok = None
        try:
            proof_dir = res.get("proof_dir")
        except Exception:
            proof_dir = None
        print("omega.ok", ok, "proof_dir", proof_dir)
except Exception as e:
    print("omega_check_error", str(e))
'@ | & $python -X utf8 -

# Optional: headless service loops (15 min)
$env:ECOSYS_HEADLESS = '1'
$env:STOP_AFTER_SEC = '900'
$headlessLog = Join-Path $run 'headless.log'
$headlessErr = Join-Path $run 'headless.err'
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $python
$psi.Arguments = '"' + (Join-Path $ROOT 'main.py') + '"'
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.UseShellExecute = $false
$psi.CreateNoWindow = $true

$proc = New-Object System.Diagnostics.Process
$proc.StartInfo = $psi
$null = $proc.Start()
$proc.Id | Out-File -FilePath (Join-Path $run 'headless.pid') -Encoding ascii
# async capture
Start-Job -ScriptBlock {
    param($p,$log,$err)
    try {
        $so = New-Object System.IO.StreamWriter($log, $true, [System.Text.UTF8Encoding]::new($false))
        $se = New-Object System.IO.StreamWriter($err, $true, [System.Text.UTF8Encoding]::new($false))
        try {
            while (-not $p.HasExited) {
                if (-not $p.StandardOutput.EndOfStream) { $so.WriteLine($p.StandardOutput.ReadLine()) }
                if (-not $p.StandardError.EndOfStream) { $se.WriteLine($p.StandardError.ReadLine()) }
                Start-Sleep -Milliseconds 100
            }
            while (-not $p.StandardOutput.EndOfStream) { $so.WriteLine($p.StandardOutput.ReadLine()) }
            while (-not $p.StandardError.EndOfStream) { $se.WriteLine($p.StandardError.ReadLine()) }
        } finally {
            $so.Close(); $se.Close()
        }
    } catch {}
} -ArgumentList $proc, $headlessLog, $headlessErr | Out-Null

Write-Output ("HEADLESS_STARTED PID=" + $proc.Id + " LOG=" + $headlessLog)
