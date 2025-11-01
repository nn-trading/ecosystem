import os, sys, json, time, shutil, sqlite3, subprocess
from pathlib import Path

ASCII_JSON_KW = dict(ensure_ascii=True, separators=(",", ":"))


def write_text_ascii(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="ascii", errors="ignore") as f:
        f.write(text)
        if not text.endswith("\n"):
            f.write("\n")


def write_json_ascii(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="ascii", errors="ignore") as f:
        json.dump(data, f, **ASCII_JSON_KW)
        f.write("\n")


def tools_registry_names(repo: Path):
    try:
        sys.path.insert(0, str(repo))
        from core.tools import REGISTRY as ToolsRegistry  # type: ignore
        names = ToolsRegistry.available() if hasattr(ToolsRegistry, "available") else []
        return {"ok": True, "names": names or []}
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


def copy_logs(repo: Path, out_dir: Path) -> None:
    logs = repo / "logs"
    try:
        tj = logs / "tasks.json"
        if tj.exists():
            shutil.copy2(str(tj), str(out_dir / "tasks.json"))
    except Exception:
        pass
    proofs_src = logs / "proofs"
    proofs_dst = out_dir / "proofs"
    if proofs_src.exists():
        for p in proofs_src.rglob("*"):
            if p.is_file():
                dst = proofs_dst / p.relative_to(proofs_src)
                dst.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(str(p), str(dst))
                except Exception:
                    try:
                        dst.write_bytes(p.read_bytes())
                    except Exception:
                        pass


def dump_sqlite(db_path: Path):
    out = {"path": str(db_path), "schema": [], "tables": {}}
    try:
        con = sqlite3.connect(str(db_path))
        cur = con.cursor()
        cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table'")
        out["schema"] = [{"name": n, "sql": s} for (n, s) in cur.fetchall()]
        for row in out["schema"]:
            name = row.get("name")
            if not name or name.startswith("sqlite_"):
                continue
            try:
                cur.execute(f"SELECT * FROM {name}")
                cols = [d[0] for d in cur.description] if cur.description else []
                rows = cur.fetchall()
                lim = 1000
                rows_out = []
                for i, r in enumerate(rows):
                    if i >= lim:
                        break
                    try:
                        rows_out.append(dict(zip(cols, r)))
                    except Exception:
                        rows_out.append({"_row": [str(x) for x in r]})
                out["tables"][name] = {"columns": cols, "rows": rows_out, "truncated": len(rows) > lim}
            except Exception as e:
                out["tables"][name] = {"error": str(e)}
        con.close()
    except Exception as e:
        out["error"] = str(e)
    return out


def dump_memory_dbs(repo: Path) -> dict:
    mem_dump = {"databases": []}
    seen = set()
    for base in (repo / "var", repo / "data"):
        if not base.exists():
            continue
        for p in base.rglob("*.db"):
            try:
                if p.exists() and p.is_file():
                    rp = str(p.resolve())
                    if rp in seen:
                        continue
                    seen.add(rp)
                    mem_dump["databases"].append(dump_sqlite(p))
            except Exception:
                continue
    return mem_dump


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    runs = repo / "runs"
    ts = os.environ.get("OMEGA_TS") or time.strftime("%Y%m%d-%H%M%S", time.localtime())
    pre = runs / ts / "preflight"
    pre.mkdir(parents=True, exist_ok=True)

    # 1) git diff
    try:
        diff = subprocess.run(["git", "diff"], cwd=str(repo), capture_output=True, text=True).stdout
    except Exception as e:
        diff = f"error: {e}"
    write_text_ascii(pre / "changes.patch", diff)

    # 2) ToolsRegistry names JSON
    tr = tools_registry_names(repo)
    write_json_ascii(pre / "tools_registry_names.json", tr.get("names") if tr.get("ok") else tr)

    # 3) copy logs/tasks.json and logs/proofs/*
    copy_logs(repo, pre)

    # 4) memory DBs
    md = dump_memory_dbs(repo)
    write_json_ascii(pre / "memory_dump.json", md)

    print(str(pre))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
