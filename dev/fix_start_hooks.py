# Fix duplicate UIA PROBE and DASHBOARD hook blocks in start.ps1 and add invocation lines
from __future__ import annotations
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / 'start.ps1'

def main() -> int:
    s = P.read_text(encoding='utf-8')
    def pat(tag: str):
        return re.compile(r'(?s)# ======= ' + re.escape(tag) + r' HOOK START =======.*?# ======= ' + re.escape(tag) + r' HOOK END =======')

    for tag in ['UIA PROBE', 'DASHBOARD']:
        rx = pat(tag)
        blocks = list(rx.finditer(s))
        if len(blocks) > 1:
            keep0 = blocks[0].group(0)
            # remove all occurrences
            s2 = rx.sub('', s)
            # insert the first one back at original first position
            start = blocks[0].start()
            s = s2[:start] + keep0 + s2[start:]
    # Ensure invocation lines exist right after each block
    ins_map = {
        'UIA PROBE': "if ($PSBoundParameters.ContainsKey('Stop') -and $Stop -eq 1) { Stop-UIAProbe } elseif ($PSBoundParameters.ContainsKey('Background') -and $Background -eq 1) { Start-UIAProbe }",
        'DASHBOARD': "if ($PSBoundParameters.ContainsKey('Stop') -and $Stop -eq 1) { Stop-Dashboard } elseif ($PSBoundParameters.ContainsKey('Background') -and $Background -eq 1) { Start-Dashboard }",
    }
    for tag, call in ins_map.items():
        rx = pat(tag)
        m = rx.search(s)
        if m:
            end = m.end()
            # insert only if not present nearby
            snippet = s[end:end+len(call)+10]
            if call not in snippet and call not in s[m.start():m.end()+200]:
                s = s[:end] + "\n" + call + "\n" + s[end:]
    P.write_text(s, encoding='utf-8')
    print('fixed start.ps1')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
