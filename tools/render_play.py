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


def draw_frame(title, subtitle, players, ball_xy, out_path, los_y=LOS_Y):
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
    d.line([(x0, los_y * s), (x1, los_y * s)], fill='black', width=3 * s)
    d.text((34 * s, (los_y + 6) * s), 'LINE OF SCRIMMAGE', font=F_SMALL, fill='black')
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
    nframes = int(FPS * play.get('dur', DUR))
    for n in range(nframes):
        t = n / FPS
        players = [(name, pos_at(wps, t)) for name, wps in play['players']]
        pmap = dict(players)
        # ball: list of (time, carrier). Carrier 'PRESNAP' floats above C.
        # A carrier of ('pass', from, to, t_end) animates the ball flying from -> to.
        carrier, ct = None, 0
        for bt, c in play['ball']:
            if t >= bt:
                carrier, ct = c, bt
        if carrier == 'PRESNAP':
            cx, cy = pmap['C']
            ball = (cx, cy - 26)
        elif isinstance(carrier, tuple) and carrier[0] == 'pass':
            _, frm, to, t_end = carrier
            f = min(1, (t - ct) / (t_end - ct)) if t_end > ct else 1
            (x0, y0), (x1, y1) = pmap[frm], pmap[to]
            ball = (x0 + (x1 - x0) * f, y0 + (y1 - y0) * f)
        else:
            ball = pmap[carrier]
        draw_frame(play['title'], play['subtitle'], players, ball, f'{outdir}/f{n:04d}.png', play.get('los_y', LOS_Y))


PLAYS = {}

# ---------------- Base Play 1: Criss-Cross ----------------
PLAYS['b1'] = {
    'title': 'Play 1: Criss-Cross Purple',
    'subtitle': 'Fake to Blue crossing right — Purple follows through, takes the handoff, and heads up the left side',
    'ball': [(0, 'PRESNAP'), (0.45, 'QB'), (1.6, 'P')],
    'players': [
        ('R', [(0, 154, 214), (0.5, 154, 214), (1.4, 154, 150), (2.5, 268, 112), (4.0, 318, 100), (5.0, 330, 96)]),
        ('G', [(0, 644, 214), (0.5, 644, 214), (1.6, 644, 142), (2.7, 545, 138), (4.0, 505, 136), (5.0, 500, 136)]),
        ('C', [(0, 399, 214), (0.7, 399, 214), (5.0, 399, 128)]),
        ('P', [(0, 514, 354), (0.6, 514, 354), (1.6, 428, 318), (2.4, 320, 296), (3.0, 268, 214), (5.0, 250, 106)]),
        ('B', [(0, 325, 345), (0.3, 325, 345), (1.1, 408, 306), (2.1, 520, 295), (2.8, 562, 214), (5.0, 588, 106)]),
        ('QB', [(0, 399, 252), (0.45, 399, 252), (1.0, 399, 288), (1.8, 399, 288), (2.6, 388, 300), (5.0, 384, 302)]),
    ],
}

# ---------------- Base Play 2: Criss-Cross Blue (mirror of Play 1) ----------------
PLAYS['b2'] = {
    'title': 'Play 2: Criss-Cross Blue',
    'subtitle': 'Fake to Purple crossing left — Blue follows through, takes the handoff, and heads up the right side',
    'ball': [(0, 'PRESNAP'), (0.45, 'QB'), (1.6, 'B')],
    'players': [
        ('R', [(0, 154, 214), (0.5, 154, 214), (1.4, 154, 150), (2.5, 268, 112), (4.0, 318, 100), (5.0, 330, 96)]),
        ('G', [(0, 644, 214), (0.5, 644, 214), (1.6, 644, 142), (2.7, 545, 138), (4.0, 505, 136), (5.0, 500, 136)]),
        ('C', [(0, 399, 214), (0.7, 399, 214), (5.0, 399, 128)]),
        ('P', [(0, 514, 354), (0.3, 514, 354), (1.1, 390, 306), (2.1, 280, 295), (2.8, 238, 214), (5.0, 212, 106)]),
        ('B', [(0, 325, 345), (0.6, 325, 345), (1.6, 370, 318), (2.4, 470, 296), (3.0, 528, 214), (5.0, 548, 100)]),
        ('QB', [(0, 399, 252), (0.45, 399, 252), (1.0, 399, 288), (1.8, 399, 288), (2.6, 388, 300), (5.0, 384, 302)]),
    ],
}

# ------------- Base Play 3: Criss-Cross Reverse -------------
PLAYS['b3'] = {
    'title': 'Play 3: Criss-Cross Reverse',
    'subtitle': 'Fake to Blue, handoff to Purple going left — Purple hands to Red on the reverse up the right side',
    'ball': [(0, 'PRESNAP'), (0.45, 'QB'), (1.5, 'P'), (2.5, 'R')],
    'players': [
        ('R', [(0, 235, 214), (0.4, 235, 214), (1.2, 205, 258), (2.0, 238, 272), (2.5, 275, 268), (3.5, 470, 262), (4.2, 590, 240), (4.5, 608, 214), (5.0, 622, 130)]),
        ('G', [(0, 644, 214), (0.5, 644, 214), (1.6, 644, 148), (2.7, 562, 142), (4.0, 540, 140), (5.0, 535, 140)]),
        ('C', [(0, 399, 214), (0.7, 399, 214), (5.0, 372, 126)]),
        ('P', [(0, 514, 354), (0.4, 514, 354), (1.5, 428, 330), (2.5, 275, 268), (3.1, 232, 214), (5.0, 212, 112)]),
        ('B', [(0, 325, 345), (0.3, 325, 345), (1.1, 408, 306), (2.1, 520, 295), (2.8, 562, 214), (5.0, 588, 106)]),
        ('QB', [(0, 399, 252), (0.45, 399, 252), (1.0, 399, 290), (1.6, 399, 290), (2.6, 390, 302), (5.0, 386, 304)]),
    ],
}

# ======= Base Plays 5-7: End-Around Red family (LOS one yard-line deeper for room) =======
EA_LOS = 290
def _ea_players(red_tail, green_tail, purple_tail):
    return [
        ('R', [(0, 154, 290), (0.4, 154, 290), (1.0, 300, 350), (1.6, 430, 372), (2.4, 590, 362), (2.9, 640, 352)] + red_tail),
        ('G', [(0, 644, 290), (0.5, 644, 290), (1.7, 644, 190), (2.7, 740, 188), (3.4, 790, 186)] + green_tail),
        ('C', [(0, 399, 290), (0.7, 399, 290), (2.4, 399, 150), (6.0, 399, 146)]),
        ('B', [(0, 325, 421), (1.5, 325, 421), (2.5, 325, 302), (6.0, 325, 300)]),
        ('P', [(0, 514, 430), (2.2, 514, 430), (3.0, 514, 302)] + purple_tail),
        ('QB', [(0, 399, 328), (0.45, 399, 328), (1.0, 399, 366), (1.6, 399, 366), (2.6, 378, 380), (6.0, 372, 384)]),
    ]

PLAYS['b5'] = {
    'title': 'Play 5: End-Around Red, Pump and Run',
    'subtitle': 'Red takes the end-around right, stops and shows pass, then tucks it and runs up the right side',
    'ball': [(0, 'PRESNAP'), (0.45, 'QB'), (1.6, 'R')],
    'los_y': EA_LOS, 'dur': 6.0,
    'players': _ea_players(
        red_tail=[(3.5, 640, 352), (4.2, 690, 290), (6.0, 704, 130)],
        green_tail=[(6.0, 830, 120)],
        purple_tail=[(6.0, 514, 300)]),
}

PLAYS['b6'] = {
    'title': 'Play 6: End-Around Red, Out to Green',
    'subtitle': 'Same end-around action — Red stops behind the line and throws the 7-yard out to Green',
    'ball': [(0, 'PRESNAP'), (0.45, 'QB'), (1.6, 'R'), (3.2, ('pass', 'R', 'G', 3.8)), (3.8, 'G')],
    'los_y': EA_LOS, 'dur': 6.0,
    'players': _ea_players(
        red_tail=[(3.6, 640, 352), (6.0, 650, 340)],
        green_tail=[(3.9, 808, 184), (6.0, 830, 100)],
        purple_tail=[(6.0, 514, 300)]),
}

PLAYS['b7'] = {
    'title': 'Play 7: End-Around Red, Shovel to Purple',
    'subtitle': 'Same end-around action — Red stops and shovels forward to Purple waiting at the line',
    'ball': [(0, 'PRESNAP'), (0.45, 'QB'), (1.6, 'R'), (3.2, ('pass', 'R', 'P', 3.5)), (3.5, 'P')],
    'los_y': EA_LOS, 'dur': 6.0,
    'players': _ea_players(
        red_tail=[(3.6, 640, 352), (6.0, 650, 340)],
        green_tail=[(6.0, 830, 120)],
        purple_tail=[(3.5, 514, 300), (4.3, 520, 240), (6.0, 526, 110)]),
}

# ------- Base Play 11: Shovel Pass to Green (must-pass) -------
PLAYS['b11'] = {
    'title': 'Play 11: Shovel Pass to Green',
    'subtitle': 'Tight line with Red wide left — everyone walks upfield, Green slides into the middle for a quick forward shovel',
    'ball': [(0, 'PRESNAP'), (0.45, 'QB'), (2.7, ('pass', 'QB', 'G', 3.0)), (3.0, 'G')],
    'players': [
        ('R', [(0, 154, 214), (0.6, 154, 214), (5.0, 154, 118)]),
        ('B', [(0, 359, 214), (0.6, 359, 214), (5.0, 359, 124)]),
        ('C', [(0, 399, 214), (0.6, 399, 214), (5.0, 399, 116)]),
        ('P', [(0, 439, 214), (0.6, 439, 214), (5.0, 439, 122)]),
        ('G', [(0, 479, 214), (0.6, 479, 214), (1.4, 440, 220), (2.3, 402, 204), (3.2, 402, 204), (5.0, 402, 150)]),
        ('QB', [(0, 399, 252), (0.45, 399, 252), (1.0, 399, 278), (3.0, 399, 278), (5.0, 392, 284)]),
    ],
}

# ------- Base Play 4: Criss-Cross Fake Reverse, Purple Keeps It -------
PLAYS['b4'] = {
    'title': 'Play 4: Criss-Cross Fake Reverse, Purple Keeps It',
    'subtitle': 'Same action as Play 3, but Purple fakes the reverse to Red, keeps it, and heads up the left side',
    'ball': [(0, 'PRESNAP'), (0.45, 'QB'), (1.5, 'P')],
    'players': [
        ('R', [(0, 235, 214), (0.4, 235, 214), (1.2, 205, 258), (2.0, 238, 272), (2.5, 275, 268), (3.5, 470, 262), (4.2, 590, 240), (4.5, 608, 214), (5.0, 622, 130)]),
        ('G', [(0, 644, 214), (0.5, 644, 214), (1.6, 644, 148), (2.7, 562, 142), (4.0, 540, 140), (5.0, 535, 140)]),
        ('C', [(0, 399, 214), (0.7, 399, 214), (5.0, 372, 126)]),
        ('P', [(0, 514, 354), (0.4, 514, 354), (1.5, 428, 330), (2.5, 275, 268), (3.1, 232, 214), (5.0, 212, 112)]),
        ('B', [(0, 325, 345), (0.3, 325, 345), (1.1, 408, 306), (2.1, 520, 295), (2.8, 562, 214), (5.0, 588, 106)]),
        ('QB', [(0, 399, 252), (0.45, 399, 252), (1.0, 399, 290), (1.6, 399, 290), (2.6, 390, 302), (5.0, 386, 304)]),
    ],
}

# ------- Base Play 14: Criss-Cross Double Fake, Quick In to Green -------
PLAYS['b14'] = {
    'title': 'Play 14: Criss-Cross Double Fake, Quick In to Green',
    'subtitle': 'Fake to Blue, fake to Purple on the criss-cross — QB throws to Green on the quick in route',
    'ball': [(0, 'PRESNAP'), (0.45, 'QB'), (2.4, ('pass', 'QB', 'G', 2.8)), (2.8, 'G')],
    'players': [
        ('R', [(0, 284, 214), (0.5, 284, 214), (1.4, 284, 150), (2.5, 360, 108), (4.0, 385, 98), (5.0, 390, 96)]),
        ('G', [(0, 644, 214), (0.4, 644, 214), (1.3, 644, 168), (2.4, 556, 164), (3.0, 520, 162), (5.0, 498, 108)]),
        ('C', [(0, 399, 214), (0.7, 399, 214), (5.0, 399, 128)]),
        ('P', [(0, 514, 354), (0.6, 514, 354), (1.6, 428, 318), (2.4, 340, 300), (3.0, 310, 214), (5.0, 293, 110)]),
        ('B', [(0, 325, 345), (0.3, 325, 345), (1.1, 408, 306), (2.1, 520, 295), (2.8, 562, 214), (5.0, 588, 106)]),
        ('QB', [(0, 399, 252), (0.45, 399, 252), (1.0, 399, 288), (2.4, 399, 288), (2.7, 394, 294), (5.0, 392, 296)]),
    ],
}

# ------- Base Play 15: Double Go, Deep Shot to Green -------
PLAYS['b15'] = {
    'title': 'Play 15: Double Go, Deep Shot to Green',
    'subtitle': 'Red and Green sprint deep on go routes — QB drops straight back and throws deep to Green',
    'ball': [(0, 'PRESNAP'), (0.45, 'QB'), (2.6, ('pass', 'QB', 'G', 4.2)), (4.2, 'G')],
    'los_y': 420,
    'dur': 6.5,
    'players': [
        ('R', [(0, 284, 420), (0.4, 284, 420), (1.6, 284, 330), (3.6, 290, 170), (5.2, 294, 105), (6.5, 296, 95)]),
        ('G', [(0, 644, 420), (0.4, 644, 420), (1.6, 642, 330), (3.5, 640, 165), (4.3, 638, 115), (6.5, 628, 88)]),
        ('C', [(0, 399, 420), (0.7, 399, 420), (6.5, 399, 356)]),
        ('P', [(0, 514, 560), (0.5, 514, 560), (2.5, 498, 432), (3.2, 494, 426), (6.5, 490, 424)]),
        ('B', [(0, 325, 551), (0.5, 325, 551), (2.5, 342, 430), (3.2, 346, 425), (6.5, 350, 423)]),
        ('QB', [(0, 399, 458), (0.45, 399, 458), (1.2, 399, 516), (2.6, 399, 516), (3.0, 396, 512), (6.5, 395, 510)]),
    ],
}

if __name__ == '__main__':
    n = sys.argv[1]
    outdir = f'.videos/frames{n}'
    render(PLAYS[n], outdir)
    subprocess.run(['ffmpeg', '-y', '-v', 'error', '-framerate', '30', '-i', f'{outdir}/f%04d.png',
                    '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                    f'.videos/play{n}.mp4'], check=True)
    print(f'rendered .videos/play{n}.mp4')
