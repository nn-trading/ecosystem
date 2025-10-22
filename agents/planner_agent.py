import asyncio, json
from pathlib import Path
from agents.base_agent import BaseAgent

# Tiny "task DSL" accepted by /plan:
#   create <path>
#   write  <path> -> <text>
#   read   <path>
#   ls     <path>
#   shell  <command> |cwd=<dir>  (cwd optional)
#
# Multiple directives separated by commas:
#   create C:\x\y, write C:\x\y\z.txt -> hello, shell dir |cwd=C:\x\y

class PlannerAgent(BaseAgent):
    async def run(self):
        await self.bus.publish("comms/out", {"text": "[Planner] online"}, sender=self.name)

        # 👉 Listen to what CommsAgent sends:
        #    Comms publishes: topic='plan/request', payload={'origin': '<spec>'}
        async for env in self.bus.subscribe("plan/request"):
            try:
                spec = (env.payload.get("origin") or "").strip()
                if not spec:
                    await self.bus.publish("comms/out",
                                           {"text": "[Planner] Empty plan spec."},
                                           sender=self.name)
                    continue

                steps = self._parse_spec(spec)
                await self.bus.publish("exec/request",
                                       {"origin": spec, "steps": steps},
                                       sender=self.name)
                await self.bus.publish("comms/out",
                                       {"text": f"[Planner] Planned {len(steps)} step(s)."},
                                       sender=self.name)
            except Exception as e:
                await self.bus.publish("comms/out",
                                       {"text": f"[Planner] Parse error: {e!r}"},
                                       sender=self.name)

    def _parse_spec(self, spec: str):
        parts = [p.strip() for p in spec.split(",") if p.strip()]
        steps = []
        for p in parts:
            low = p.lower()

            if low.startswith("write "):
                rest = p[6:].strip()
                if "->" not in rest:
                    raise ValueError(f"write missing '->': {p}")
                path, text = rest.split("->", 1)
                steps.append({"tool": "fs.write",
                              "args": {"path": path.strip(), "text": text.strip()}})

            elif low.startswith("read "):
                path = p[5:].strip()
                steps.append({"tool": "fs.read", "args": {"path": path}})

            elif low.startswith("ls "):
                path = p[3:].strip()
                steps.append({"tool": "fs.ls", "args": {"path": path}})

            elif low.startswith("shell "):
                body = p[6:].strip()
                cwd = None
                if "|cwd=" in body:
                    cmd_part, cwd_part = body.split("|cwd=", 1)
                    body = cmd_part.strip().strip('"')
                    cwd = cwd_part.strip().strip('"')
                steps.append({"tool": "shell.run",
                              "args": {"cmd": body, **({"cwd": cwd} if cwd else {})}})

            elif low.startswith("create "):
                target = p[7:].strip()
                name = Path(target).name
                looks_dir = (("." not in name) or target.endswith("\\") or target.endswith("/"))
                if looks_dir:
                    steps.append({"tool": "shell.run",
                                  "args": {"cmd": f'mkdir "{target}"'}})
                else:
                    steps.append({"tool": "fs.write",
                                  "args": {"path": target, "text": ""}})
            else:
                raise ValueError(f"Unknown directive: {p}")
        return steps
