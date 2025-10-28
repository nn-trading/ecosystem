import os, subprocess, sys

def test_list_tasks_shows_count_and_categories():
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    py = os.path.join(repo, '.venv', 'Scripts', 'python.exe')
    cmd = [py, os.path.join(repo, 'tools', 'eval_runner.py'), '--list']
    out = subprocess.check_output(cmd, text=True, encoding='utf-8', errors='ignore')
    assert 'Total:' in out
    # spot-check some categories appear in listing
    assert '\tstrings\t' in out or '\tmath\t' in out


def test_filter_runs_subset():
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    py = os.path.join(repo, '.venv', 'Scripts', 'python.exe')
    cmd = [py, os.path.join(repo, 'tools', 'eval_runner.py'), '--filter', 'strings']
    proc = subprocess.run(cmd, text=True, encoding='utf-8', errors='ignore', stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    out = proc.stdout
    assert 'Evaluation Summary' in out
    assert 'Ran:' in out
