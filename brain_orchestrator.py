import os, sys, json, time, argparse, subprocess, textwrap, re
from datetime import datetime
import requests

OPENAI_API_BASE = os.environ.get('OPENAI_API_BASE', 'https://openrouter.ai/api/v1')
OPENAI_API_KEY  = os.environ.get('OPENAI_API_KEY', '')
OPENAI_MODEL    = os.environ.get('OPENAI_MODEL', 'openai/gpt-oss-20b')

TOOLS_PY = r"C:\\bots\\ecosys\\tools\\gui_tool.py"
WEB_PY   = r"C:\\bots\\ecosys\\tools\\web_tool.py"
FILE_PY  = r"C:\\bots\\ecosys\\tools\\file_tool.py"
APP_PY   = r"C:\\bots\\ecosys\\tools\\app_tool.py"
HOTKEY_PY= r"C:\\bots\\ecosys\\tools\\hotkey_tool.py"
PYTHON   = r"C:\\bots\\ecosys\\.venv\\Scripts\\python.exe"
REPORTS  = r"C:\\bots\\ecosys\\reports"

ALLOWED_TOOLS = {
    'openurl','window','type','click','move','hotkey','scroll','screenshot','ocr',
    'shell','wait','web_play','web_get', 'app_open','app_close','app_focus','app_list',
    'file_download','press'
}

SCHEMA = textwrap.dedent("""\
You control a Windows PC through these tools (emit JSON actions):
- openurl {url, timeout?, keep_open?, page_shot?, fullpage?}    # headful Playwright + optional page screenshot
- window {title}
- type {text, enter?}
- click {x?, y?, button?=(left|right|middle), double?}
- move {x, y, relative?, duration?}
- press {keys CSV, interval?, e.g. "enter,enter"}
- hotkey {combo, interval?}
- scroll {amount (pos=up, neg=down)}
- screenshot {path?, monitor? (int)}                             # OS-level desktop capture (monitor 0 = full desktop)
- ocr {image}
- wait {seconds}                                                 # prefer over shell sleeps

- file_download {url, out, timeout?}

- shell {cmd}                                                    # filesystem/CLI tasks only (not for delays)
- web_play {url, wait_selector?, timeout?, page_shot (abs path)?, fullpage?, html_out (abs path)?, eval_selector?}  # headless Playwright
- web_get {url, save?, headers?}                                 # simple HTTP GET via requests

- app_open {path?, name?, args?}                              # open app via Start-Process or by image name
- app_close {name? pid?}                                      # taskkill by name or PID
- app_focus {title? pid?}                                     # focus a window by substring title or PID
- app_list {filter?}                                          # list visible windows


Rules:
- Return ONLY strict JSON: {plan: string, actions: [ {tool, args} ], stop: bool, next_prompt: string|null}.
- Use openurl timeout/keep_open for on-screen browsing; use web_play for headless fetch/page_shot/html_out.
- Prefer wait over shell for delays. Use shell only when necessary.
- For proofs, save under C:\\\\bots\\\\ecosys\\\\reports\\\\screens\\\\ or \\\\proofs\\\\.
- Keep plans short and concrete.
""")

def call_chat(messages, temperature=0.2):
    url = OPENAI_API_BASE.rstrip('/') + '/chat/completions'
    headers = {'Authorization': f'Bearer {OPENAI_API_KEY}', 'Content-Type':'application/json'}
    body = {'model': OPENAI_MODEL, 'messages': messages, 'temperature': temperature}
    r = requests.post(url, headers=headers, data=json.dumps(body), timeout=120)
    r.raise_for_status()
    data = r.json()
    msg = data.get('choices', [{}])[0].get('message', {}).get('content') or ''
    return msg, data

def extract_json(s):
    m = re.search(r'\{[\s\S]*\}', s)
    if m:
        try: return json.loads(m.group(0))
        except Exception: pass
    try: return json.loads(s)
    except Exception: return None

def _run_python_tool(pyfile, subcmd, args_dict, timeout=180):
    cmd = [PYTHON, pyfile, subcmd]
    for k, v in (args_dict or {}).items():
        # Skip null-like values entirely
        if v is None or (isinstance(v, str) and v.strip().lower() == 'none'):
            continue
        flag = f'--{str(k).replace("_","-")}'
        if isinstance(v, bool):
            # Only pass boolean flags that are true AND correspond to switch-like args.
            # If a boolean mistakenly appears for an option that expects a value (e.g., page-shot), skip it.
            if v and k not in {'page_shot','html_out','eval_selector','url','save','headers','wait_selector'}:
                cmd.append(flag)
        else:
            cmd.extend([flag, str(v)])
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    txt = out.stdout.strip() or out.stderr.strip()
    try:
        return json.loads(txt)
    except Exception:
        return {'ok': False, 'raw': txt, 'rc': out.returncode}

def run_action(tool, args):
    # wait
    if tool == 'wait':
        secs = 0.0
        try:
            secs = float((args or {}).get('seconds', 0))
        except Exception:
            secs = 0.0
        try:
            time.sleep(secs); return {'ok': True, 'action': 'wait', 'seconds': secs}
        except Exception as e:
            return {'ok': False, 'error': str(e), 'tool': 'wait', 'args': args}

    # shell
    if tool == 'shell':
        cmd = (args or {}).get('cmd') or (args or {}).get('command')
        if not cmd: return {'ok': False, 'error': 'missing cmd'}
        try:
            out = subprocess.run(['powershell','-NoProfile','-ExecutionPolicy','Bypass','-Command', cmd],
                                 capture_output=True, text=True, timeout=300)
            return {'ok': out.returncode == 0, 'rc': out.returncode, 'stdout': out.stdout, 'stderr': out.stderr}
        except Exception as e:
            return {'ok': False, 'error': str(e), 'tool': 'shell', 'args': args}

    # gui_tool mapped actions
    if tool in {'openurl','window','type','click','move','scroll','screenshot','ocr'}:
        return _run_python_tool(TOOLS_PY, tool, args or {}, timeout=240)

    # web_tool mapped actions
    if tool == 'web_play':
        a = dict(args or {})
        try:
            url = str(a.get('url',''))
        except Exception:
            url = ''
        # Inject auto-consent by default for Google domains (maps to --auto-consent in web_tool.py)
        if ('google.' in url.lower()) and ('auto_consent' not in a):
            a['auto_consent'] = True
        # Normalize boolean + *_path into concrete values the tool expects
        ps = a.get('page_shot')
        pspath = a.pop('page_shot_path', None)
        if isinstance(ps, bool):
            if pspath:
                a['page_shot'] = pspath
            elif ps is False:
                a.pop('page_shot', None)
        hs = a.get('html_out')
        hspath = a.pop('html_out_path', None)
        if isinstance(hs, bool):
            if hspath:
                a['html_out'] = hspath
            elif hs is False:
                a.pop('html_out', None)
        # Normalize eval_selector for common mistakes like 'document.title'
        if str(a.get('eval_selector','')).strip().lower() in {'document.title','doc.title','page.title','window.title'}:
            a['eval_selector'] = 'title'
        return _run_python_tool(WEB_PY, 'play', a, timeout=240)
    if tool == 'web_get':
        return _run_python_tool(WEB_PY, 'get', args or {}, timeout=240)
    if isinstance(tool, str) and tool.startswith('app_'):
        sub = tool.split('_',1)[1]
        if sub in {'open','close','focus','list'}:
            return _run_python_tool(APP_PY, sub, args or {}, timeout=180)

    if tool == 'file_download':
        return _run_python_tool(FILE_PY, 'download', args or {}, timeout=180)
    if tool == 'hotkey':
        return _run_python_tool(HOTKEY_PY, 'hotkey', args or {}, timeout=60)
    if tool == 'press':
        return _run_python_tool(HOTKEY_PY, 'press', args or {}, timeout=60)

    return {'ok': False, 'error': 'unknown tool', 'tool': tool}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--goal', required=True)
    ap.add_argument('--max_iters', type=int, default=3)
    args = ap.parse_args()

    os.makedirs(REPORTS, exist_ok=True)
    os.makedirs(os.path.join(REPORTS, 'screens'), exist_ok=True)
    os.makedirs(os.path.join(REPORTS, 'proofs'), exist_ok=True)

    if not OPENAI_API_KEY:
        print('[ERROR] Missing OPENAI_API_KEY env. Run use_gptoss.ps1 first.', file=sys.stderr); sys.exit(1)

    messages = [
        {'role':'system','content': SCHEMA},
        {'role':'user','content': f'GOAL: {args.goal}'}
    ]
    observations, all_steps = [], []
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_json = os.path.join(REPORTS, f'actions_{ts}.json')

    for step in range(1, args.max_iters+1):
        if observations:
            messages.append({'role':'system','content': 'OBSERVATIONS: ' + json.dumps(observations, ensure_ascii=False)[:6000]})
        reply, raw = call_chat(messages)
        plan_obj = extract_json(reply)
        all_steps.append({'step': step, 'assistant_reply': reply, 'raw': raw})

        if not plan_obj or 'actions' not in plan_obj:
            observations.append({'step': step, 'ok': False, 'error': 'bad or missing JSON/actions', 'assistant_reply': reply})
            messages.append({'role':'user','content':'Your last message was not valid JSON per the schema. Please resend strictly JSON.'})
            continue

        plan = plan_obj.get('plan','')
        actions = plan_obj.get('actions',[]) or []
        stop = bool(plan_obj.get('stop', False))
        next_prompt = plan_obj.get('next_prompt')

        step_obs = {'step': step, 'plan': plan, 'actions': [], 'stop': stop}
        for act in actions:
            tool = (act.get('tool') or '').strip()
            a = act.get('args') or {}
            if tool not in ALLOWED_TOOLS:
                step_obs['actions'].append({'tool': tool, 'ok': False, 'error': 'unknown tool'}); continue
            res = run_action(tool, a)
            step_obs['actions'].append({'tool': tool, 'args': a, 'result': res})
        observations.append(step_obs)

        with open(log_json, 'w', encoding='utf-8') as f:
            json.dump({'goal': args.goal, 'steps': all_steps, 'observations': observations}, f, ensure_ascii=False, indent=2)

        if stop: break
        messages.append({'role':'user','content': next_prompt or 'Proceed to completion or ask one concise question if needed.'})

    print(json.dumps({'ok': True, 'goal': args.goal, 'log': log_json, 'iters': len(observations)}, ensure_ascii=False))

if __name__ == '__main__':
    main()
