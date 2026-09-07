#!/usr/bin/env python3
"""Recover player waypoints from an existing playbook MP4 by tracking dot colors.

Usage: track_video.py <key>   (e.g. b9) — extracts the MP4 for that key from index.html,
dumps frames, tracks each dot's centroid, simplifies to waypoints, prints a PLAYS[] block.
"""
import os, re, sys, base64, subprocess, shutil
import numpy as np
from PIL import Image

COL = {'R': (255, 107, 107), 'B': (91, 141, 239), 'G': (94, 200, 94),
       'P': (155, 109, 215), 'C': (208, 208, 208), 'QB': (255, 248, 208), 'BALL': (139, 69, 19)}
FPS = 30

def extract(key, out):
    html = open('index.html').read()
    m = re.search(rf'"{key}": \{{ title: "[^"]*", desc: "[^"]*", src: "data:video/mp4;base64,([A-Za-z0-9+/=]+)"', html)
    open(out, 'wb').write(base64.b64decode(m.group(1)))

def track_frame(path):
    a = np.asarray(Image.open(path).convert('RGB')).astype(int)[84:616, 24:936]
    out = {}
    for k, c in COL.items():
        m = (np.abs(a - np.array(c)).sum(axis=2) < (60 if k == 'BALL' else 45))
        m2 = m[2:-2] & m[:-4] & m[4:]
        ys, xs = np.nonzero(m2)
        out[k] = (xs.mean() + 24, ys.mean() + 86) if len(xs) >= (8 if k == 'BALL' else 20) else None
    return out

def rdp(pts, eps):
    """Ramer-Douglas-Peucker on (t, x, y) with t scaled to px."""
    if len(pts) < 3: return pts
    a, b = np.array(pts[0]), np.array(pts[-1])
    ab = b - a; n = np.linalg.norm(ab)
    d = [np.linalg.norm(np.cross(ab, np.array(p) - a)) / n if n else np.linalg.norm(np.array(p) - a) for p in pts]
    i = int(np.argmax(d))
    if d[i] > eps:
        return rdp(pts[:i + 1], eps)[:-1] + rdp(pts[i:], eps)
    return [pts[0], pts[-1]]

def main(key):
    mp4 = f'.videos/orig_{key}.mp4'; fdir = f'.videos/orig_{key}_frames'
    extract(key, mp4)
    if os.path.isdir(fdir): shutil.rmtree(fdir)
    os.makedirs(fdir)
    subprocess.run(['ffmpeg', '-v', 'error', '-i', mp4, f'{fdir}/f%04d.png'], check=True)
    frames = sorted(os.listdir(fdir))
    tracks = [track_frame(f'{fdir}/{f}') for f in frames]
    dur = len(frames) / FPS
    print(f"# {key}: {len(frames)} frames, {dur:.1f}s")
    for name in ('R', 'G', 'C', 'P', 'B', 'QB'):
        pts = [(n / FPS, *tr[name]) for n, tr in enumerate(tracks) if tr[name]]
        simp = rdp([(t * 80, x, y) for t, x, y in pts], 4.0)
        wps = [(round(t / 80, 2), round(x), round(y)) for t, x, y in simp]
        print(f"        ('{name}', {wps}),")
    # ball carrier per 0.1s
    print("# ball (t: nearest dot, dist):")
    line = []
    for n in range(0, len(tracks), 3):
        b = tracks[n]['BALL']
        if not b: line.append(f"{n/FPS:.1f}:-"); continue
        d = {k: np.hypot(v[0]-b[0], v[1]-b[1]) for k, v in tracks[n].items() if k != 'BALL' and v}
        k = min(d, key=d.get); line.append(f"{n/FPS:.1f}:{k}({d[k]:.0f})")
    print(' '.join(line))

if __name__ == '__main__':
    main(sys.argv[1])
