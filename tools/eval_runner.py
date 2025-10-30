from __future__ import annotations
import argparse, os, sys, json, csv, sqlite3, re, hashlib, zipfile, gzip, io, random, statistics, shutil, time, math, asyncio, glob
from dataclasses import dataclass
from typing import Callable, Dict, Any, List, Tuple

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
VAR_DIR = os.path.join(REPO, 'var')
RESULTS_PATH = os.path.join(VAR_DIR, 'eval_results.jsonl')
SANDBOX = os.path.join(REPO, 'workspace', 'eval_sandbox')

@dataclass
class Task:
    id: str
    category: str
    name: str
    func: Callable[[], Tuple[bool, Dict[str, Any]]]

    def run(self) -> Dict[str, Any]:
        started = time.time()
        try:
            ok, info = self.func()
            status = 'pass' if ok else 'fail'
            err = None
        except Exception as e:
            ok = False
            status = 'error'
            info = {}
            err = f"{e.__class__.__name__}: {e}"
        dur = time.time() - started
        return {
            'id': self.id,
            'category': self.category,
            'name': self.name,
            'status': status,
            'ok': ok,
            'duration_sec': round(dur, 6),
            'info': info,
            'timestamp': int(time.time()),
        }

# Utilities

def ensure_dirs():
    os.makedirs(VAR_DIR, exist_ok=True)
    os.makedirs(SANDBOX, exist_ok=True)

# Category generators

def gen_string_tasks(prefix: str='STR') -> List[Task]:
    tasks: List[Task] = []
    samples = [
        'Hello World', 'ecosystem ai', 'TEST case', '  trim  ', 'Palindrome',
        'racecar', 'A man, a plan, a canal: Panama', 'foo-bar_baz', '123abc', 'Mixed CASES'
    ]
    vowels = set('aeiouAEIOU')

    def t_reverse(s: str) -> Task:
        def fn():
            return s[::-1] == ''.join(reversed(s)), {'input': s}
        return Task(f'{prefix}-REV-{hash(s)%10000}', 'strings', f'reverse:{s}', fn)

    def t_upper(s: str) -> Task:
        def fn():
            return s.upper() == ''.join([c.upper() for c in s]), {'input': s}
        return Task(f'{prefix}-UP-{hash(s)%10000}', 'strings', f'upper:{s}', fn)

    def t_lower(s: str) -> Task:
        def fn():
            return s.lower() == ''.join([c.lower() for c in s]), {'input': s}
        return Task(f'{prefix}-LOW-{hash(s)%10000}', 'strings', f'lower:{s}', fn)

    def t_trim(s: str) -> Task:
        def fn():
            return s.strip() == re.sub(r'^[\s\uFEFF\u200B]+|[\s\uFEFF\u200B]+$', '', s), {'input': s}
        return Task(f'{prefix}-TRIM-{hash(s)%10000}', 'strings', f'trim:{s}', fn)

    def t_vowel_count(s: str) -> Task:
        def fn():
            cnt = sum(1 for c in s if c in vowels)
            cnt2 = len([c for c in s if c in vowels])
            return cnt == cnt2, {'input': s, 'vowels': cnt}
        return Task(f'{prefix}-VCOUNT-{hash(s)%10000}', 'strings', f'vowel_count:{s}', fn)

    def t_palindrome(s: str) -> Task:
        def fn():
            cleaned = re.sub(r'[^A-Za-z0-9]', '', s).lower()
            return cleaned == cleaned[::-1], {'input': s, 'cleaned': cleaned}
        return Task(f'{prefix}-PAL-{hash(s)%10000}', 'strings', f'palindrome_check:{s}', fn)

    def t_unique_chars(s: str) -> Task:
        def fn():
            return len(set(s)) == len({c for c in s}), {'input': s}
        return Task(f'{prefix}-UNIQ-{hash(s)%10000}', 'strings', f'unique_char_count:{s}', fn)

    def t_split_join(s: str) -> Task:
        def fn():
            parts = s.split(' ')
            joined = ' '.join(parts)
            return joined == s, {'parts': parts}
        return Task(f'{prefix}-SPLJ-{hash(s)%10000}', 'strings', f'split_join:{s}', fn)

    gens = [t_reverse, t_upper, t_lower, t_trim, t_vowel_count, t_palindrome, t_unique_chars, t_split_join]
    for s in samples:
        for g in gens:
            tasks.append(g(s))
    # Add some substring/index tasks
    for i, s in enumerate(samples):
        needle = 'a'
        def mk(s=s, i=i):
            def fn():
                idx = s.find(needle)
                ok = (idx == -1) or (s[idx] == needle)
                return ok, {'input': s, 'needle': needle, 'index': idx}
            return Task(f'{prefix}-FIND-{i}', 'strings', f'find:{needle} in sample#{i}', fn)
        tasks.append(mk())
    return tasks[:30]  # cap ~30 tasks


def gen_math_tasks(prefix: str='MTH') -> List[Task]:
    tasks: List[Task] = []
    nums = list(range(0, 21))

    def factorial(n: int) -> int:
        return math.prod(range(1, n+1)) if n > 1 else (0 if n == 0 else 1)

    for n in nums[:11]:
        def mk(n=n):
            def fn():
                # Compare iterative vs recursive style results
                it = factorial(n)
                rec = 1
                for k in range(2, n+1):
                    rec *= k
                return it == rec, {'n': n, 'fact': it}
            return Task(f'{prefix}-FACT-{n}', 'math', f'factorial:{n}', fn)
        tasks.append(mk())

    pairs = [(a, b) for a in range(1, 21, 3) for b in range(1, 21, 4)]
    for i, (a, b) in enumerate(pairs[:12]):
        def mk(a=a, b=b, i=i):
            def fn():
                g = math.gcd(a, b)
                # Validate gcd property
                return (a % g == 0 and b % g == 0), {'a': a, 'b': b, 'gcd': g}
            return Task(f'{prefix}-GCD-{i}', 'math', f'gcd:{a},{b}', fn)
        tasks.append(mk())

    primes = [2,3,5,7,11,13,17,19]
    for p in primes:
        def mk(p=p):
            def fn():
                # trial division
                if p < 2: return False, {'n': p}
                ok = True
                for d in range(2, int(p**0.5)+1):
                    if p % d == 0:
                        ok = False; break
                return ok, {'n': p}
            return Task(f'{prefix}-PRIME-{p}', 'math', f'prime:{p}', fn)
        tasks.append(mk())

    # Fibonacci checks
    for n in range(1, 11):
        def mk(n=n):
            def fib(k):
                a,b=0,1
                for _ in range(k):
                    a,b=b,a+b
                return a
            def fn():
                return fib(n) >= 1 if n>0 else True, {'n': n}
            return Task(f'{prefix}-FIB-{n}', 'math', f'fib:{n}', fn)
        tasks.append(mk())

    # Averages/median
    for i in range(1, 6):
        arr = [random.randint(0, 100) for _ in range(25)]
        def mk(arr=arr, i=i):
            def fn():
                mean = sum(arr)/len(arr)
                med = statistics.median(arr)
                return (min(arr) <= med <= max(arr)) and (min(arr) <= mean <= max(arr)), {'n': len(arr)}
            return Task(f'{prefix}-STATS-{i}', 'math', f'stats:{i}', fn)
        tasks.append(mk())
    return tasks[:30]


def gen_file_tasks(prefix: str='FILE') -> List[Task]:
    ensure_dirs()
    tasks: List[Task] = []
    base = os.path.join(SANDBOX, 'files')
    os.makedirs(base, exist_ok=True)

    # Create 10 files with content and verify roundtrip
    for i in range(10):
        p = os.path.join(base, f'f{i}.txt')
        content = f'line1-{i}\nline2-{i}\n'
        def mk(p=p, content=content, i=i):
            def fn():
                with open(p, 'w', encoding='ascii', errors='ignore') as f:
                    f.write(content)
                with open(p, 'r', encoding='utf-8') as f:
                    rd = f.read()
                return rd == content, {'path': p}
            return Task(f'{prefix}-CREATE-{i}', 'fileops', f'create_read:{i}', fn)
        tasks.append(mk())

    # Copy and move operations
    def copy_move_task(idx: int):
        src = os.path.join(base, f'f{idx}.txt')
        cp = os.path.join(base, f'f{idx}.copy.txt')
        mv = os.path.join(base, f'f{idx}.moved.txt')
        def fn():
            shutil.copy2(src, cp)
            ok1 = os.path.exists(cp) and os.path.getsize(cp) == os.path.getsize(src)
            shutil.move(cp, mv)
            ok2 = os.path.exists(mv) and not os.path.exists(cp)
            return (ok1 and ok2), {'src': src, 'mv': mv}
        return Task(f'{prefix}-CPMV-{idx}', 'fileops', f'copy_move:{idx}', fn)
    for i in range(5):
        tasks.append(copy_move_task(i))

    # Glob and size aggregation
    def glob_size():
        def fn():
            files = glob.glob(os.path.join(base, '*.txt'))
            total = sum(os.path.getsize(p) for p in files)
            return total > 0 and len(files) >= 10, {'count': len(files), 'total': total}
        return Task(f'{prefix}-GLOB', 'fileops', 'glob_and_size', fn)
    tasks.append(glob_size())

    # Rename and delete
    def rename_delete(idx: int):
        p = os.path.join(base, f'f{idx}.txt')
        q = os.path.join(base, f'f{idx}.renamed.txt')
        def fn():
            os.replace(p, q)
            ok1 = os.path.exists(q) and not os.path.exists(p)
            os.remove(q)
            return ok1 and (not os.path.exists(q)), {'renamed': q}
        return Task(f'{prefix}-REDEL-{idx}', 'fileops', f'rename_delete:{idx}', fn)
    for i in range(5):
        tasks.append(rename_delete(i))

    return tasks[:20]


def gen_json_tasks(prefix: str='JSON') -> List[Task]:
    tasks: List[Task] = []
    objs = [
        {'a': 1, 'b': [1,2,3], 'c': {'x': True}},
        {'msg': 'hello', 'nums': list(range(5))},
        {'nested': {'k': 'v', 'n': None}},
        {'float': 3.14159, 'bool': False, 'arr': ['x','y']},
        {'unicode': 'Café', 'emoji': 'ok'}
    ]
    for i, obj in enumerate(objs):
        def mk(obj=obj, i=i):
            def fn():
                s = json.dumps(obj, ensure_ascii=True)
                back = json.loads(s)
                return back == obj, {'json_len': len(s)}
            return Task(f'{prefix}-RT-{i}', 'json', f'roundtrip:{i}', fn)
        tasks.append(mk())
    # Pretty print stability (keys order for dicts not guaranteed, check reparse equality)
    for i, obj in enumerate(objs):
        def mk(obj=obj, i=i):
            def fn():
                s = json.dumps(obj, indent=2, sort_keys=True)
                back = json.loads(s)
                return back == obj, {'indent': 2}
            return Task(f'{prefix}-PRETTY-{i}', 'json', f'pretty:{i}', fn)
        tasks.append(mk())
    return tasks[:10]


def gen_csv_tasks(prefix: str='CSV') -> List[Task]:
    tasks: List[Task] = []
    ensure_dirs()
    path = os.path.join(SANDBOX, 'data.csv')
    rows = [(i, i*i, i%3) for i in range(50)]

    def write_csv():
        def fn():
            with open(path, 'w', newline='', encoding='ascii', errors='ignore') as f:
                w = csv.writer(f)
                w.writerow(['n','sq','mod3'])
                w.writerows(rows)
            return os.path.exists(path) and os.path.getsize(path) > 0, {'path': path}
        return Task(f'{prefix}-WRITE', 'csv', 'write', fn)

    def read_agg():
        def fn():
            with open(path, 'r', newline='', encoding='utf-8') as f:
                r = csv.DictReader(f)
                total = sum(int(row['sq']) for row in r)
            expected = sum(i*i for i in range(50))
            return total == expected, {'sum_sq': total}
        return Task(f'{prefix}-AGG', 'csv', 'aggregate', fn)

    def filter_rows():
        def fn():
            with open(path, 'r', newline='', encoding='utf-8') as f:
                r = csv.DictReader(f)
                cnt = sum(1 for row in r if int(row['mod3']) == 0)
            return cnt == len([i for i in range(50) if i%3==0]), {'count_mod0': cnt}
        return Task(f'{prefix}-FILTER', 'csv', 'filter', fn)

    tasks += [write_csv(), read_agg(), filter_rows()]
    # replicate small variations to increase count
    for i in range(7):
        def mk(i=i):
            def fn():
                with open(path, 'r', encoding='utf-8') as f:
                    data = f.read()
                return ('mod3' in data) and ('sq' in data), {'len': len(data)}
            return Task(f'{prefix}-SCAN-{i}', 'csv', f'scan:{i}', fn)
        tasks.append(mk())
    return tasks[:10]


def gen_sqlite_tasks(prefix: str='SQL') -> List[Task]:
    tasks: List[Task] = []
    ensure_dirs()
    db = os.path.join(SANDBOX, 'eval.db')

    def init_db():
        def fn():
            if os.path.exists(db): os.remove(db)
            conn = sqlite3.connect(db)
            c = conn.cursor()
            c.execute('CREATE TABLE t (id INTEGER PRIMARY KEY, n INT, sq INT)')
            conn.commit(); conn.close()
            return os.path.exists(db), {'db': db}
        return Task(f'{prefix}-INIT', 'sqlite', 'init_db', fn)

    tasks.append(init_db())

    def insert_rows():
        def fn():
            conn = sqlite3.connect(db)
            c = conn.cursor()
            rows = [(i, i*i) for i in range(100)]
            c.executemany('INSERT INTO t (n, sq) VALUES (?,?)', rows)
            conn.commit(); conn.close()
            return True, {'inserted': 100}
        return Task(f'{prefix}-INS', 'sqlite', 'insert_rows', fn)
    tasks.append(insert_rows())

    def count_rows():
        def fn():
            conn = sqlite3.connect(db)
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM t')
            cnt = c.fetchone()[0]
            conn.close()
            return cnt == 100, {'count': cnt}
        return Task(f'{prefix}-COUNT', 'sqlite', 'count_rows', fn)
    tasks.append(count_rows())

    def sum_sq():
        def fn():
            conn = sqlite3.connect(db)
            c = conn.cursor()
            c.execute('SELECT SUM(sq) FROM t')
            total = c.fetchone()[0]
            conn.close()
            return total == sum(i*i for i in range(100)), {'sum_sq': total}
        return Task(f'{prefix}-SUM', 'sqlite', 'sum_sq', fn)
    tasks.append(sum_sq())

    # Index and query
    def create_index():
        def fn():
            conn = sqlite3.connect(db)
            c = conn.cursor()
            c.execute('CREATE INDEX ix_t_sq ON t(sq)')
            conn.commit(); conn.close()
            return True, {'indexed': True}
        return Task(f'{prefix}-INDEX', 'sqlite', 'create_index', fn)
    tasks.append(create_index())

    # A few parameterized queries
    for k in range(5):
        n = random.randint(0, 99)
        def mk(k=k, n=n):
            def fn():
                conn = sqlite3.connect(db)
                c = conn.cursor()
                c.execute('SELECT sq FROM t WHERE n=?', (n,))
                row = c.fetchone(); conn.close()
                return (row is not None) and (row[0] == n*n), {'n': n}
            return Task(f'{prefix}-GET-{k}', 'sqlite', f'get_sq:{n}', fn)
        tasks.append(mk())
    return tasks[:10]


def gen_regex_tasks(prefix: str='RE') -> List[Task]:
    tasks: List[Task] = []
    emails = ['a@b.com','user.name+tag@domain.co','bad@domain','x@y.z']
    for i, e in enumerate(emails):
        def mk(e=e, i=i):
            def fn():
                pat = re.compile(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
                ok = bool(pat.match(e))
                return ok == (e.count('@')==1 and '.' in e.split('@')[1]), {'email': e, 'match': ok}
            return Task(f'{prefix}-EMAIL-{i}', 'regex', f'email:{i}', fn)
        tasks.append(mk())
    texts = ['Visit http://example.com now', 'No url here', 'https://a.b', 'ftp://host']
    for i, t in enumerate(texts):
        def mk(t=t, i=i):
            def fn():
                ok = bool(re.search(r'https?://\S+', t))
                return ok == ('http' in t or 'https' in t), {'text': t}
            return Task(f'{prefix}-URL-{i}', 'regex', f'url:{i}', fn)
        tasks.append(mk())
    # Replacement
    def replace():
        def fn():
            s = 'abc123def456'
            out = re.sub(r'\d+', '#', s)
            return out == 'abc#def#', {'out': out}
        return Task(f'{prefix}-SUB', 'regex', 'sub_digits', fn)
    tasks.append(replace())
    return tasks[:10]


def gen_hash_zip_tasks(prefix: str='HZ') -> List[Task]:
    tasks: List[Task] = []
    ensure_dirs()
    base = os.path.join(SANDBOX, 'hz')
    os.makedirs(base, exist_ok=True)
    src = os.path.join(base, 'data.txt')
    with open(src, 'w', encoding='utf-8') as f:
        f.write('hello world' * 100)

    def sha256_task():
        def fn():
            h = hashlib.sha256()
            with open(src, 'rb') as f:
                h.update(f.read())
            digest = h.hexdigest()
            return len(digest) == 64, {'sha256': digest}
        return Task(f'{prefix}-SHA', 'hash_zip', 'sha256', fn)
    tasks.append(sha256_task())

    def zip_task():
        def fn():
            zp = os.path.join(base, 'data.zip')
            with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
                z.write(src, arcname='data.txt')
            ok = os.path.exists(zp) and os.path.getsize(zp) > 0
            with zipfile.ZipFile(zp, 'r') as z:
                with z.open('data.txt') as f:
                    txt = f.read().decode('utf-8')
            return ok and txt.startswith('hello'), {'zip': zp}
        return Task(f'{prefix}-ZIP', 'hash_zip', 'zip_roundtrip', fn)
    tasks.append(zip_task())

    def gzip_task():
        def fn():
            gp = os.path.join(base, 'data.txt.gz')
            with open(src, 'rb') as f_in, gzip.open(gp, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
            with gzip.open(gp, 'rb') as f_in:
                data = f_in.read()
            return data.startswith(b'hello'), {'gz': gp}
        return Task(f'{prefix}-GZ', 'hash_zip', 'gzip_roundtrip', fn)
    tasks.append(gzip_task())

    # Duplicate small variations to reach ~10
    for i in range(7):
        def mk(i=i):
            def fn():
                h = hashlib.md5(b'block-%d' % i).hexdigest()
                return len(h) == 32, {'md5': h}
            return Task(f'{prefix}-MD5-{i}', 'hash_zip', f'md5:{i}', fn)
        tasks.append(mk())
    return tasks[:10]


def gen_async_tasks(prefix: str='ASY') -> List[Task]:
    tasks: List[Task] = []
    async def work(x):
        await asyncio.sleep(0)
        return x*x

    for i in range(5):
        def mk(i=i):
            def fn():
                async def run():
                    res = await asyncio.gather(*[work(k) for k in range(i+1)])
                    return sum(res)
                total = asyncio.run(run())
                expected = sum(k*k for k in range(i+1))
                return total == expected, {'n': i+1}
            return Task(f'{prefix}-GATH-{i}', 'async', f'gather:{i}', fn)
        tasks.append(mk())
    return tasks[:5]


def gen_datetime_tasks(prefix: str='DT') -> List[Task]:
    import datetime as dt
    tasks: List[Task] = []

    def parse_iso(s: str, i: int):
        def fn():
            t = dt.datetime.fromisoformat(s)
            return t.isoformat() == s, {'s': s}
        return Task(f'{prefix}-ISO-{i}', 'datetime', f'iso:{i}', fn)

    samples = ['2025-10-27T19:00:00', '2022-01-01T00:00:00', '2030-12-31T23:59:59']
    for i, s in enumerate(samples):
        tasks.append(parse_iso(s, i))

    def delta():
        def fn():
            a = dt.datetime(2020,1,1)
            b = dt.datetime(2020,1,31)
            d = (b-a).days
            return d == 30, {'days': d}
        return Task(f'{prefix}-DELTA', 'datetime', 'delta_days', fn)
    tasks.append(delta())

    def format_task():
        def fn():
            t = dt.datetime(2025,10,27,19,0,0)
            s = t.strftime('%Y-%m-%d %H:%M')
            return s == '2025-10-27 19:00', {'fmt': s}
        return Task(f'{prefix}-FMT', 'datetime', 'format', fn)
    tasks.append(format_task())

    # Add 5 arithmetic cases
    for i in range(5):
        def mk(i=i):
            def fn():
                t = dt.datetime(2020,1,1) + dt.timedelta(days=i)
                return t.day == 1 + i, {'day': t.day}
            return Task(f'{prefix}-ADD-{i}', 'datetime', f'add_days:{i}', fn)
        tasks.append(mk())
    return tasks[:10]


def gen_algo_tasks(prefix: str='ALG') -> List[Task]:
    tasks: List[Task] = []
    data = [random.randint(0,1000) for _ in range(100)]

    def sort_nums():
        def fn():
            arr = list(data)
            arr.sort()
            return arr == sorted(data), {'n': len(arr)}
        return Task(f'{prefix}-SORT', 'algorithms', 'sort', fn)
    tasks.append(sort_nums())

    def top_k(k: int):
        def fn():
            arr = sorted(data, reverse=True)[:k]
            return arr == sorted(data, reverse=True)[:k], {'k': k}
        return Task(f'{prefix}-TOP-{k}', 'algorithms', f'top{k}', fn)
    for k in [1,3,5,10]: tasks.append(top_k(k))

    def binary_search():
        def fn():
            arr = sorted(set(data))
            target = arr[len(arr)//2]
            # classic binary search
            lo, hi = 0, len(arr)-1
            while lo <= hi:
                mid = (lo+hi)//2
                if arr[mid] == target: return True, {'target': target}
                if arr[mid] < target: lo = mid+1
                else: hi = mid-1
            return False, {'target': target}
        return Task(f'{prefix}-BINS', 'algorithms', 'binary_search', fn)
    tasks.append(binary_search())

    # Sorting dicts by key
    def sort_dicts():
        def fn():
            arr = [{'x': i, 'y': i%3} for i in range(20)]
            out = sorted(arr, key=lambda r: (-r['y'], r['x']))
            ok = all(out[i]['y'] >= out[i+1]['y'] or (out[i]['y']==out[i+1]['y'] and out[i]['x']<=out[i+1]['x']) for i in range(len(out)-1))
            return ok, {'n': len(out)}
        return Task(f'{prefix}-SDICT', 'algorithms', 'sort_dicts', fn)
    tasks.append(sort_dicts())

    # Path/glob small checks
    def glob_check():
        def fn():
            pats = glob.glob(os.path.join(REPO, 'core', '*.py'))
            return len(pats) >= 1, {'count': len(pats)}
        return Task(f'{prefix}-GLOB', 'algorithms', 'glob_core_py', fn)
    tasks.append(glob_check())

    # Add more tiny algorithm checks to reach ~10
    for i in range(3):
        def mk(i=i):
            def fn():
                arr = [random.randint(0,50) for _ in range(25)]
                s1 = sum(arr)
                s2 = 0
                for v in arr: s2 += v
                return s1 == s2, {'n': len(arr)}
            return Task(f'{prefix}-SUM-{i}', 'algorithms', f'sum_loop:{i}', fn)
        tasks.append(mk())
    return tasks[:10]


def collect_tasks() -> List[Task]:
    tasks: List[Task] = []
    tasks += gen_string_tasks()
    tasks += gen_math_tasks()
    tasks += gen_file_tasks()
    tasks += gen_json_tasks()
    tasks += gen_csv_tasks()
    tasks += gen_sqlite_tasks()
    tasks += gen_regex_tasks()
    tasks += gen_hash_zip_tasks()
    tasks += gen_async_tasks()
    tasks += gen_datetime_tasks()
    tasks += gen_algo_tasks()
    return tasks


def write_result(rec: Dict[str, Any]):
    with open(RESULTS_PATH, 'a', encoding='ascii', errors='ignore') as f:
        f.write(json.dumps(rec, ensure_ascii=True) + '\n')


def main():
    ensure_dirs()
    parser = argparse.ArgumentParser(description='Ecosystem AI evaluation harness')
    parser.add_argument('--list', action='store_true', help='List tasks and exit')
    parser.add_argument('--filter', type=str, default='', help='Substring filter on id/name/category')
    parser.add_argument('--category', type=str, default='', help='Run only a specific category')
    parser.add_argument('--clean', action='store_true', help='Clean sandbox before run')
    args = parser.parse_args()

    if args.clean and os.path.exists(SANDBOX):
        shutil.rmtree(SANDBOX, ignore_errors=True)
    ensure_dirs()

    tasks = collect_tasks()
    if args.list:
        for t in tasks:
            print(f"{t.id}\t{t.category}\t{t.name}")
        print(f"Total: {len(tasks)} tasks")
        return 0

    # Apply filters
    if args.category:
        tasks = [t for t in tasks if t.category == args.category]
    if args.filter:
        q = args.filter.lower()
        tasks = [t for t in tasks if (q in t.id.lower() or q in t.category.lower() or q in t.name.lower())]

    if not tasks:
        print('No tasks to run after filtering.')
        return 1

    # Run
    passed = 0
    failed = 0
    errors = 0
    start = time.time()
    for t in tasks:
        rec = t.run()
        write_result(rec)
        if rec['status'] == 'pass':
            passed += 1
        elif rec['status'] == 'fail':
            failed += 1
        else:
            errors += 1
    dur = time.time() - start

    print('--- Evaluation Summary ---')
    print(f"Ran: {len(tasks)} tasks")
    print(f"Pass: {passed}  Fail: {failed}  Error: {errors}")
    print(f"Duration: {dur:.3f}s")

    # Print simple per-category counts
    cats: Dict[str, int] = {}
    for t in tasks:
        cats[t.category] = cats.get(t.category, 0) + 1
    print('By category:', cats)
    return 0 if (failed == 0 and errors == 0) else 2

if __name__ == '__main__':
    sys.exit(main())

