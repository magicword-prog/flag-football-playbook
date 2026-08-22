#!/usr/bin/env python3
"""Render playbook animation frames in the established style (960x640, 30fps, 5s)."""
import os, sys, subprocess, shutil
from PIL import Image, ImageDraw, ImageFont

W, H = 960, 640
SS = 2  # supersample
FPS, DUR = 30, 5.0
NFRAMES = int(FPS * DUR)

FIELD = (20, 80, 938, 618)
LOS_Y = 214
YARD_YS = [150, 290, 360, 430, 500, 570]

COL = {
    'R': (255, 107, 107), 'B': (91, 141, 239), 'G': (94, 200, 94),
    'P': (155, 109, 215), 'C': (208, 208, 208), 'QB': (255, 248, 208),
}
DARK_TEXT = {'C', 'QB'}

F_TITLE = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 22 * SS)
F_SUB = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 13 * SS)
F_SMALL = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 10 * SS)
F_DOT = ImageFont.truetype('/System/Library/Fonts/Helvetica.ttc', 12 * SS, index=1)  # bold


def smoothstep(t):
    return t * t * (3 - 2 * t)


def pos_at(waypoints, t):
    """waypoints: list of (time, x, y); linear segments with smoothstep easing."""
    if t <= waypoints[0][0]:
        return waypoints[0][1], waypoints[0][2]
    for i in range(len(waypoints) - 1):
        t0, x0, y0 = waypoints[i]
        t1, x1, y1 = waypoints[i + 1]
        if t0 <= t <= t1:
            f = smoothstep((t - t0) / (t1 - t0)) if t1 > t0 else 1
            return x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
    return waypoints[-1][1], waypoints[-1][2]


def draw_frame(title, subtitle, players, ball_xy, out_path):
    img = Image.new('RGB', (W * SS, H * SS), 'white')
    d = ImageDraw.Draw(img)
    s = SS
    # title
    tw = d.textlength(title, font=F_TITLE)
    d.text(((W * s - tw) / 2, 12 * s), title, font=F_TITLE, fill='black')
    sw = d.textlength(subtitle, font=F_SUB)
    d.text(((W * s - sw) / 2, 40 * s), subtitle, font=F_SUB, fill=(100, 100, 100))
    # field
    x0, y0, x1, y1 = [v * s for v in FIELD]
    for yy in YARD_YS:
        d.line([(x0, yy * s), (x1, yy * s)], fill=(211, 211, 211), width=s)
    d.rectangle([x0, y0, x1, y1], outline='black', width=2 * s)
    d.line([(x0, LOS_Y * s), (x1, LOS_Y * s)], fill='black', width=3 * s)
    d.text((34 * s, 220 * s), 'LINE OF SCRIMMAGE', font=F_SMALL, fill='black')
    d.text((800 * s, 88 * s), '^ Direction of Play', font=F_SMALL, fill='black')
    # players (draw order: line players first, then backs, QB last so overlaps look right)
    r = 15 * s
    for name, (px, py) in players:
        cx, cy = px * s, py * s
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=COL[name], outline='black', width=2 * s)
        label = name
        fill = (40, 40, 40) if name in DARK_TEXT else 'white'
        lw = d.textlength(label, font=F_DOT)
        bbox = F_DOT.getbbox(label)
        lh = bbox[3] - bbox[1]
        d.text((cx - lw / 2, cy - lh / 2 - bbox[1]), label, font=F_DOT, fill=fill)
    # football
    if ball_xy:
        bx, by = ball_xy[0] * s, ball_xy[1] * s
        bw, bh = 10 * s, 6 * s
        d.ellipse([bx - bw, by - bh, bx + bw, by + bh], fill=(139, 69, 19), outline='black', width=s)
        d.line([(bx - 5 * s, by), (bx + 5 * s, by)], fill='white', width=s)
        for lx in (-3, 0, 3):
            d.line([(bx + lx * s, by - 2 * s), (bx + lx * s, by + 2 * s)], fill='white', width=s)
    img = img.resize((W, H), Image.LANCZOS)
    img.save(out_path)


def render(play, outdir):
    if os.path.isdir(outdir):
        shutil.rmtree(outdir)
    os.makedirs(outdir)
    for n in range(NFRAMES):
        t = n / FPS
        players = [(name, pos_at(wps, t)) for name, wps in play['players']]
        pmap = dict(players)
        # ball: list of (time, carrier_or_xy). Carrier 'PRESNAP' floats above C.
        carrier = None
        for bt, c in play['ball']:
            if t >= bt:
                carrier = c
        if carrier == 'PRESNAP':
            cx, cy = pmap['C']
            ball = (cx, cy - 26)
        else:
            ball = pmap[carrier]
        draw_frame(play['title'], play['subtitle'], players, ball, f'{outdir}/f{n:04d}.png')


PLAYS = {}

# ---------------- Play 11: Criss-Cross ----------------
PLAYS[11] = {
    'title': 'Play 11: Criss-Cross',
    'subtitle': 'Fake to Purple crossing right — Blue follows through, takes the handoff, and heads up the left side',
    'ball': [(0, 'PRESNAP'), (0.45, 'QB'), (1.6, 'B')],
    'players': [
        ('R', [(0, 284, 214), (0.5, 284, 214), (1.4, 284, 150), (2.5, 360, 108), (4.0, 385, 98), (5.0, 390, 96)]),
        ('G', [(0, 644, 214), (0.5, 644, 214), (1.6, 644, 142), (2.7, 560, 138), (4.0, 535, 136), (5.0, 530, 136)]),
        ('C', [(0, 399, 214), (0.7, 399, 214), (5.0, 399, 128)]),
        ('B', [(0, 514, 354), (0.6, 514, 354), (1.6, 428, 318), (2.4, 340, 300), (3.0, 310, 214), (5.0, 293, 110)]),
        ('P', [(0, 325, 345), (0.3, 325, 345), (1.1, 408, 306), (2.1, 520, 295), (2.8, 562, 214), (5.0, 588, 106)]),
        ('QB', [(0, 399, 252), (0.45, 399, 252), (1.0, 399, 288), (1.8, 399, 288), (2.6, 388, 300), (5.0, 384, 302)]),
    ],
}

# ------------- Play 12: Criss-Cross Reverse -------------
PLAYS[12] = {
    'title': 'Play 12: Criss-Cross Reverse',
    'subtitle': 'Fake to Purple, handoff to Blue going left — Blue hands to Red on the reverse up the right side',
    'ball': [(0, 'PRESNAP'), (0.45, 'QB'), (1.5, 'B'), (2.5, 'R')],
    'players': [
        ('R', [(0, 235, 214), (0.4, 235, 214), (1.2, 205, 258), (2.0, 238, 272), (2.5, 275, 268), (3.5, 470, 262), (4.2, 590, 240), (4.5, 608, 214), (5.0, 622, 130)]),
        ('G', [(0, 644, 214), (0.5, 644, 214), (1.6, 644, 148), (2.7, 562, 142), (4.0, 540, 140), (5.0, 535, 140)]),
        ('C', [(0, 399, 214), (0.7, 399, 214), (5.0, 372, 126)]),
        ('B', [(0, 514, 354), (0.4, 514, 354), (1.5, 428, 330), (2.5, 275, 268), (3.1, 232, 214), (5.0, 212, 112)]),
        ('P', [(0, 325, 345), (0.3, 325, 345), (1.1, 408, 306), (2.1, 520, 295), (2.8, 562, 214), (5.0, 588, 106)]),
        ('QB', [(0, 399, 252), (0.45, 399, 252), (1.0, 399, 290), (1.6, 399, 290), (2.6, 390, 302), (5.0, 386, 304)]),
    ],
}

# ------- Play 14: Criss-Cross Quick Handoff to Purple -------
PLAYS[14] = {
    'title': 'Play 14: Criss-Cross Quick Handoff to Purple',
    'subtitle': 'Same criss-cross action, but Purple takes a quick handoff on his first cross and runs up the right side',
    'ball': [(0, 'PRESNAP'), (0.45, 'QB'), (1.1, 'P')],
    'players': [
        ('R', [(0, 284, 214), (0.5, 284, 214), (1.4, 284, 150), (2.5, 360, 108), (4.0, 385, 98), (5.0, 390, 96)]),
        ('G', [(0, 644, 214), (0.5, 644, 214), (1.6, 644, 142), (2.7, 560, 138), (4.0, 535, 136), (5.0, 530, 136)]),
        ('C', [(0, 399, 214), (0.7, 399, 214), (5.0, 399, 128)]),
        ('B', [(0, 514, 354), (0.6, 514, 354), (1.6, 428, 318), (2.4, 340, 300), (3.0, 310, 214), (5.0, 293, 110)]),
        ('P', [(0, 325, 345), (0.3, 325, 345), (1.1, 408, 306), (2.1, 520, 295), (2.8, 562, 214), (5.0, 588, 106)]),
        ('QB', [(0, 399, 252), (0.45, 399, 252), (1.0, 399, 288), (1.8, 399, 288), (2.6, 388, 300), (5.0, 384, 302)]),
    ],
}

# ------- Play 13: Criss-Cross Fake Reverse, Blue Keeps It -------
PLAYS[13] = {
    'title': 'Play 13: Criss-Cross Fake Reverse, Blue Keeps It',
    'subtitle': 'Same action as Play 12, but Blue fakes the reverse to Red, keeps it, and heads up the left side',
    'ball': [(0, 'PRESNAP'), (0.45, 'QB'), (1.5, 'B')],
    'players': [
        ('R', [(0, 235, 214), (0.4, 235, 214), (1.2, 205, 258), (2.0, 238, 272), (2.5, 275, 268), (3.5, 470, 262), (4.2, 590, 240), (4.5, 608, 214), (5.0, 622, 130)]),
        ('G', [(0, 644, 214), (0.5, 644, 214), (1.6, 644, 148), (2.7, 562, 142), (4.0, 540, 140), (5.0, 535, 140)]),
        ('C', [(0, 399, 214), (0.7, 399, 214), (5.0, 372, 126)]),
        ('B', [(0, 514, 354), (0.4, 514, 354), (1.5, 428, 330), (2.5, 275, 268), (3.1, 232, 214), (5.0, 212, 112)]),
        ('P', [(0, 325, 345), (0.3, 325, 345), (1.1, 408, 306), (2.1, 520, 295), (2.8, 562, 214), (5.0, 588, 106)]),
        ('QB', [(0, 399, 252), (0.45, 399, 252), (1.0, 399, 290), (1.6, 399, 290), (2.6, 390, 302), (5.0, 386, 304)]),
    ],
}

if __name__ == '__main__':
    n = int(sys.argv[1])
    outdir = f'.videos/frames{n}'
    render(PLAYS[n], outdir)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-framerate', '30', '-i', f'{outdir}/f%04d.png',
                    '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                    f'.videos/play{n}.mp4'], check=True)
    print(f'rendered .videos/play{n}.mp4')
