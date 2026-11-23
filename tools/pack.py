"""Pack the page's footage, desktop and phone sets.

  python tools/pack.py turn <person.mp4> <matte.mp4> <key> [--from N --to M]
  python tools/pack.py city <flyover.mp4> <key>

turn: the person (top half) and its Alpha Gen matte (bottom half) stacked in one video, so one seek moves both.
      Only frames N..M (the turn itself) are kept. A keyframe every 8 frames keeps scrubbing smooth at a third of the
      weight of an all-keyframe file.  desktop: 1280x1440, crf 20   phone: 1280x1440, crf 24
city: the flyover that runs through the person and behind them.          desktop: 960x540, crf 26   phone: 640x360, crf 28
Writes media/<kind>-<key>.mp4 (desktop) and media/m/<kind>-<key>.mp4 (phones).
"""
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'media'
SETS = {'turn': [(OUT, 1280, 720, 20), (OUT / 'm', 1280, 720, 24)], 'city': [(OUT, 960, 540, 26), (OUT / 'm', 640, 360, 28)]}
X264 = ['-c:v', 'libx264', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-an', '-movflags', '+faststart']


def arg(name, default):
    return int(sys.argv[sys.argv.index(name) + 1]) if name in sys.argv else default


kind = sys.argv[1]
if kind == 'turn':
    person, matte, key = sys.argv[2:5]
    a, b = arg('--from', 0), arg('--to', 10 ** 6)
    for d, w, h, crf in SETS['turn']:
        d.mkdir(parents=True, exist_ok=True)
        cut = f'trim=start_frame={a}:end_frame={b + 1},setpts=PTS-STARTPTS'
        fc = (f'[0]{cut},scale={w}:{h}:flags=lanczos,format=yuv420p[p];'
              f'[1]{cut},scale={w}:{h}:flags=lanczos,format=yuv420p[m];[p][m]vstack')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', person, '-i', matte, '-filter_complex', fc, '-r', '24',
                        *X264, '-crf', str(crf), '-g', '8', '-bf', '0', str(d / f'turn-{key}.mp4')], check=True)
elif kind == 'city':
    src, key = sys.argv[2:4]
    for d, w, h, crf in SETS['city']:
        d.mkdir(parents=True, exist_ok=True)
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-vf', f'scale={w}:{h}:flags=lanczos', *X264, '-crf', str(crf),
                        str(d / f'city-{key}.mp4')], check=True)
for f in sorted(OUT.glob(f'**/{kind}-*{sys.argv[-1] if kind == "city" else sys.argv[4]}.mp4')):
    print(f.relative_to(ROOT), f'{f.stat().st_size / 1e6:.2f} MB')
