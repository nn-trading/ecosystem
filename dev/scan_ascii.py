import os, sys, json

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

non_ascii_names = []
md_heading_violations = []

for dirpath, dirnames, filenames in os.walk(ROOT):
    for name in list(dirnames) + list(filenames):
        p = os.path.join(dirpath, name)
        try:
            name.encode('ascii')
        except Exception:
            non_ascii_names.append(p)

for dirpath, _, filenames in os.walk(ROOT):
    for fn in filenames:
        if fn.lower().endswith('.md'):
            path = os.path.join(dirpath, fn)
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    for i, line in enumerate(f, 1):
                        s = line.lstrip()
                        if s.startswith('#'):
                            heading_text = s.lstrip('#').strip()
                            try:
                                heading_text.encode('ascii')
                            except Exception:
                                md_heading_violations.append({
                                    'path': path,
                                    'line': i,
                                    'heading': heading_text,
                                })
            except Exception as e:
                md_heading_violations.append({'path': path, 'line': 0, 'heading': f'<read_error: {e}>'})

print(json.dumps({
    'non_ascii_filenames': non_ascii_names,
    'md_heading_violations': md_heading_violations,
}, ensure_ascii=True))
