#!/usr/bin/env python3
"""Hourly job: read the sheet (CSV), render READY rows ahead, then post ONE reel via the Make webhook."""
import os, io, csv, json, time, subprocess, urllib.request
from render import render
D = os.path.dirname(os.path.abspath(__file__))
CSV_URL, POST_URL, REPO = os.environ['SHEET_CSV_URL'], os.environ['POST_URL'], os.environ['GITHUB_REPOSITORY']
MAX_RENDER, POSTS = int(os.environ.get('MAX_RENDER', '60')), int(os.environ.get('POSTS_PER_RUN', '1'))
VID, LOG = os.path.join(D, 'videos'), os.path.join(D, 'posted.txt'); os.makedirs(VID, exist_ok=True)
g = lambda *a: subprocess.run(['git', *a], check=True)
def push(msg):
    g('add', '-A'); 
    if subprocess.run(['git', 'diff', '--cached', '--quiet']).returncode == 0: return
    g('config', 'user.name', 'reel-bot'); g('config', 'user.email', 'bot@users.noreply.github.com'); g('commit', '-m', msg)
    for _ in range(4):
        if subprocess.run(['git', 'push']).returncode == 0: return
        g('pull', '--rebase')
    raise SystemExit('push failed')

raw = urllib.request.urlopen(CSV_URL, timeout=60).read().decode('utf-8-sig')
rows = list(csv.reader(io.StringIO(raw))); head = [h.strip().lower() for h in rows[0]]
col = {k: head.index(k) for k in ('no.', 'text', 'status', 'caption')}
get = lambda r, k: (r[col[k]] if col[k] < len(r) else '').strip()
ready = []   # (sheet_row, no, text, caption), sheet order = oldest first
for i, r in enumerate(rows[1:], start=2):
    if get(r, 'status').upper() == 'READY' and get(r, 'text'): ready.append((i, get(r, 'no.') or str(i), get(r, 'text'), get(r, 'caption')))
name = lambda row, no: f"mfa_{int(float(no)):05d}" if no.replace('.', '', 1).isdigit() else f"mfa_row{row}"
lines = [l.split() for l in open(LOG) if l.strip()] if os.path.exists(LOG) else []
posted = {l[0] for l in lines}
recent = sum(1 for l in lines if len(l) > 1 and time.time() - float(l[1]) < 86400)   # posts in last 24h (Instagram API cap is ~100/24h)
MAX_24H = int(os.environ.get('MAX_24H', '95'))

n = 0
for row, no, text, cap in ready:                       # 1) render ahead
    p = os.path.join(VID, name(row, no) + '.mp4')
    if os.path.exists(p) or n >= MAX_RENDER: continue
    render(text, p); n += 1; print('rendered', p)
push(f'render {n} reels')
sha = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip()

sent = 0
for row, no, text, cap in ready:                       # 2) post oldest unposted READY reel(s)
    nm = name(row, no)
    if sent >= POSTS or recent + sent >= MAX_24H: break
    if nm in posted or not os.path.exists(os.path.join(VID, nm + '.mp4')): continue
    open(LOG, 'a').write(f'{nm} {time.time():.0f}\n'); push(f'mark {nm} posted')   # log first: never double-post
    if n: time.sleep(20)                                          # let jsDelivr see the new commit
    body = json.dumps({'row': row, 'video_url': f'https://cdn.jsdelivr.net/gh/{REPO}@{sha}/videos/{nm}.mp4', 'caption': cap}).encode()
    urllib.request.urlopen(urllib.request.Request(POST_URL, body, {'Content-Type': 'application/json'}), timeout=120).read()
    print('sent to Make:', nm); sent += 1
print(f'{n} rendered, {sent} sent, {len(ready)} READY in sheet')
