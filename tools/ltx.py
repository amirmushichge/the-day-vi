"""LTX API jobs (LTX-2.5 image-to-video, LTX Alpha Gen) with a spend ledger. Python 3, standard library only.

  python tools/ltx.py video prompts/ltx-jobs.json <job name> --budget 10    # renders footage/<job>/source.mp4
  python tools/ltx.py alpha footage/<job> --budget 10                       # adds footage/<job>/matte.mp4

Key: LTX_API_KEY in .env at the repo root (see .env.example) or in the environment. It is never printed.
Every submission writes an 'uncertain' marker first; a job with a marker is resumed, never paid for twice.
--budget is a hard stop in USD across everything in footage/ledger.jsonl.
"""
import base64, json, os, sys, time, urllib.error, urllib.parse, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = 'https://api.ltx.io/v2/'
PRICE = {'ltx-2-5-fast': 0.13, 'ltx-2-5-pro': 0.17, 'alpha': 0.10}   # USD per second, 1080p (docs.ltx.io/pricing, checked 2026-11-16)
LEDGER = ROOT / 'footage' / 'ledger.jsonl'


def key():
    env = ROOT / '.env'
    if env.exists():
        for line in env.read_text(encoding='utf-8-sig').splitlines():
            k, _, v = line.partition('=')
            if k.strip() == 'LTX_API_KEY' and v.strip():
                return v.strip().strip('"\'')
    k = os.environ.get('LTX_API_KEY') or os.environ.get('LTXV_API_KEY')
    if not k:
        sys.exit('No LTX key in .env or environment')
    return k


KEY = key()


def call(method, endpoint, body=None):
    req = urllib.request.Request(API + endpoint, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={'Authorization': 'Bearer ' + KEY, 'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'LTX HTTP {e.code}: {e.read().decode()[:1500]}') from None


def spent():
    if not LEDGER.exists():
        return 0.0
    return sum(json.loads(l)['est_usd'] for l in LEDGER.read_text().splitlines() if l.strip())


def save(p, v):
    p.write_text(json.dumps(v, indent=2), encoding='utf-8')


def run(d, prefix, endpoint, body, safe, est, budget, fields):
    d.mkdir(parents=True, exist_ok=True)
    receipt, uncertain = d / f'{prefix}-receipt.json', d / f'{prefix}-uncertain.json'
    if not receipt.exists():
        if uncertain.exists():
            sys.exit(f'{d.name}: a submission may be in flight; check LTX history before retrying')
        if spent() + est > budget + 1e-9:
            sys.exit(f'budget ${budget}: spent ${spent():.2f} + ${est:.2f} is over')
        save(d / f'{prefix}-request.json', {'endpoint': endpoint, 'payload': safe, 'est_usd': est})
        save(uncertain, {'status': 'submission_in_flight'})
        res = call('POST', endpoint, body)
        save(receipt, res)
        uncertain.unlink()
        LEDGER.parent.mkdir(exist_ok=True)
        with LEDGER.open('a') as f:
            f.write(json.dumps({'t': time.strftime('%Y-%m-%dT%H:%M:%S'), 'job': f'{d.name}/{prefix}', 'id': res['id'], 'est_usd': est}) + '\n')
    res = json.loads(receipt.read_text())
    print(f'{d.name}/{prefix}: {res["id"]}', flush=True)
    for _ in range(360):
        st = call('GET', f'{endpoint}/{urllib.parse.quote(res["id"], safe="")}')
        if st['status'] in ('completed', 'failed'):
            save(d / f'{prefix}-terminal.json', st)
            if st['status'] != 'completed':
                sys.exit(f'{d.name}/{prefix} failed: {json.dumps(st.get("error"))}')
            for field, name in fields.items():
                url = st['result'][field]
                host = urllib.parse.urlsplit(url).hostname or ''
                if not (host == 'storage.googleapis.com' or host.endswith(('.ltx.io', '.ltx.video', '.lightricks.com'))):
                    sys.exit(f'unexpected output host {host}')
                urllib.request.urlretrieve(url, d / name)
                print(f'  saved {d / name} ({(d / name).stat().st_size} bytes)', flush=True)
            return st
        time.sleep(5)
    sys.exit('still running; rerun the same command to resume')


cmd = sys.argv[1]
budget = float(sys.argv[sys.argv.index('--budget') + 1])
if cmd == 'video':
    spec = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8-sig'))
    job = spec['jobs'][sys.argv[3]]
    img = ROOT / job['image']
    uri = 'data:image/png;base64,' + base64.b64encode(img.read_bytes()).decode()
    body = {'model': job['model'], 'resolution': job.get('resolution', '1920x1080'), 'fps': job.get('fps', 24),
            'generate_audio': False, 'duration': job['duration'], 'prompt': job['prompt'], 'image_uri': uri,
            'camera_motion': job.get('camera_motion', 'static')}
    safe = {**body, 'image_uri': job['image']}
    run(ROOT / 'footage' / sys.argv[3], 'video', 'image-to-video', body, safe, PRICE[job['model']] * job['duration'], budget,
        {'video_url': 'source.mp4'})
elif cmd == 'alpha':
    d = ROOT / sys.argv[2]
    term = json.loads((d / 'video-terminal.json').read_text())
    req = json.loads((d / 'video-request.json').read_text())
    body = {'video_uri': term['result']['video_url']}
    run(d, 'alpha', 'video-alpha-gen', body, {'video_uri': '(source.mp4 of this job)'}, PRICE['alpha'] * req['payload']['duration'], budget,
        {'matte_video_url': 'matte.mp4'})
