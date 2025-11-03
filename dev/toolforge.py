import os, json, time, shutil, re, sys
from pathlib import Path
import yaml
from dataclasses import dataclass

# ASCII-only log helper

def log(msg):
    try:
        print(str(msg))
    except Exception:
        print(re.sub(r"[^\x20-\x7E]", "?", str(msg)))

@dataclass
class TFConfig:
    inbox_dir: str
    processed_dir: str
    registry_file: str
    template_module: str
    template_cli: str
    tool_block_begin: str
    tool_block_end: str

    @staticmethod
    def load(repo_root: Path) -> "TFConfig":
        cfgp = repo_root / "config" / "toolforge.yaml"
        with open(cfgp, "r", encoding="utf-8") as f:
            y = yaml.safe_load(f) or {}
        return TFConfig(
            inbox_dir=str(repo_root / (y.get("inbox_dir") or "reports/inbox_tools")),
            processed_dir=str(repo_root / (y.get("processed_dir") or "reports/processed_tools")),
            registry_file=str(repo_root / (y.get("registry_file") or "tools/registry_local.json")),
            template_module=str(repo_root / (y.get("templates", {}).get("py_module") or "dev/templates/module_py.txt")),
            template_cli=str(repo_root / (y.get("templates", {}).get("cli_entry") or "dev/templates/cli_entry_py.txt")),
            tool_block_begin=y.get("start_markers", {}).get("tool_block_begin", "# ======= TOOL HOOK START ======="),
            tool_block_end=y.get("start_markers", {}).get("tool_block_end", "# ======= TOOL HOOK END ======="),
        )

class ToolForge:
    def __init__(self, repo_root: str | Path):
        self.root = Path(repo_root)
        self.cfg = TFConfig.load(self.root)
        Path(self.cfg.inbox_dir).mkdir(parents=True, exist_ok=True)
        Path(self.cfg.processed_dir).mkdir(parents=True, exist_ok=True)
        Path(self.cfg.registry_file).parent.mkdir(parents=True, exist_ok=True)

    def load_templates(self):
        with open(self.cfg.template_module, "r", encoding="utf-8") as f:
            mod_t = f.read()
        with open(self.cfg.template_cli, "r", encoding="utf-8") as f:
            cli_t = f.read()
        return mod_t, cli_t

    def _subst(self, s: str, mapping: dict) -> str:
        out = s
        for k, v in mapping.items():
            out = out.replace("${"+k+"}", str(v))
        return out

    def process_spec(self, spec_path: Path) -> dict:
        try:
            with open(spec_path, "r", encoding="utf-8") as f:
                spec = yaml.safe_load(f) or {}
        except Exception as e:
            return {"ok": False, "error": f"spec load failed: {e}"}

        name = spec.get("name") or "tool"
        mod_name = spec.get("module") or re.sub(r"[^a-zA-Z0-9_]", "_", name.lower())
        entry = spec.get("entry", "init")
        pkg_dir = self.root / "tools" / mod_name
        pkg_dir.mkdir(parents=True, exist_ok=True)
        init_py = pkg_dir / "__init__.py"
        main_py = pkg_dir / f"{mod_name}.py"
        cli_py = pkg_dir / f"{mod_name}_cli.py"

        ts = time.strftime("%Y%m%d_%H%M%S")
        mod_t, cli_t = self.load_templates()
        mapping = {
            "ModuleName": mod_name,
            "Timestamp": ts,
            "CliName": f"{mod_name}_cli",
            "ImportModule": f"tools.{mod_name}.{mod_name}",
            "EntryFunc": entry,
        }

        if not init_py.exists():
            init_py.write_text("", encoding="utf-8")
        main_py.write_text(self._subst(mod_t, mapping), encoding="utf-8")
        cli_py.write_text(self._subst(cli_t, mapping), encoding="utf-8")

        reg = {}
        if Path(self.cfg.registry_file).exists():
            try:
                reg = json.loads(Path(self.cfg.registry_file).read_text(encoding="utf-8") or "{}")
            except Exception:
                reg = {}
        reg[mod_name] = {"module": f"tools.{mod_name}.{mod_name}", "entry": entry, "updated": ts}
        Path(self.cfg.registry_file).write_text(json.dumps(reg, indent=2), encoding="utf-8")
        return {"ok": True, "name": mod_name, "files": [str(main_py), str(cli_py)]}

    def move_processed(self, spec_path: Path, result: dict):
        dst = Path(self.cfg.processed_dir) / (spec_path.name + ".done")
        try:
            shutil.move(str(spec_path), str(dst))
        except Exception:
            try:
                dst.write_text(spec_path.read_text(encoding="utf-8"), encoding="utf-8")
                spec_path.unlink(missing_ok=True)
            except Exception:
                pass

    def run_once(self) -> dict:
        inbox = Path(self.cfg.inbox_dir)
        specs = sorted([p for p in inbox.glob("*.yaml")])
        if not specs:
            return {"ok": True, "processed": 0}
        results = []
        for sp in specs:
            res = self.process_spec(sp)
            results.append(res)
            self.move_processed(sp, res)
        return {"ok": True, "processed": len(results), "results": results}

if __name__ == "__main__":
    root = os.environ.get("ECOSYS_REPO_ROOT") or Path(__file__).resolve().parents[1]
    tf = ToolForge(root)
    out = tf.run_once()
    print(json.dumps(out))
