#!/usr/bin/env python3
"""Format « photo annotée » Patte a Patte (style lignes fines sur vraie photo).
Usage :
  python3 annotate.py grille  photo.jpg sortie_dir JOB
  python3 annotate.py final   photo.jpg sortie_dir JOB   (lit TITRE et ANNOTATIONS dans l'environnement)
ANNOTATIONS = JSON : [{"x":52,"y":30,"tx":80,"ty":18,"texte":"Oreilles en arrière : inquiet"}, ...]
Coordonnées en % de l'image finale 1080x1350.
"""
import sys, os, json, textwrap
import numpy as np
from PIL import Image, ImageOps, ImageEnhance, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1350
mode, photo, out, job = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
os.makedirs(out, exist_ok=True)
POLICES = ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf']
police = next((p for p in POLICES if os.path.exists(p)), None)
def font(sz):
    return ImageFont.truetype(police, sz) if police else ImageFont.load_default()

def base_film(path):
    im = Image.open(path).convert('RGB')
    im = ImageOps.fit(im, (W, H), Image.LANCZOS, centering=(0.5, 0.45))
    im = ImageEnhance.Color(im).enhance(0.82)
    im = ImageEnhance.Contrast(im).enhance(0.94)
    a = np.asarray(im).astype(np.float32)
    a[..., 0] *= 1.03; a[..., 2] *= 0.96            # tons chauds argentique
    a += np.random.default_rng(7).normal(0, 7, a.shape[:2])[..., None]  # grain
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2)
    a *= (1 - 0.28 * np.clip(d - 0.55, 0, 1))[..., None]  # vignette douce
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

def P(px, py):
    return (px / 100.0 * W, py / 100.0 * H)

def calque():
    return Image.new('RGBA', (W, H), (0, 0, 0, 0))

def ligne(d, a, b, larg=3):
    d.line([(a[0] + 2, a[1] + 2), (b[0] + 2, b[1] + 2)], fill=(0, 0, 0, 110), width=larg)
    d.line([a, b], fill=(255, 255, 255, 235), width=larg)

def texte(d, xy, s, sz, ancre='lm', larg_max=20):
    f = font(sz)
    lignes = textwrap.wrap(s, larg_max) or ['']
    hl = sz * 1.18
    y0 = xy[1] - hl * (len(lignes) - 1) / 2
    for i, l in enumerate(lignes):
        p = (xy[0], y0 + i * hl)
        for dx, dy in ((2, 2), (1, 2), (2, 1)):
            d.text((p[0] + dx, p[1] + dy), l, font=f, fill=(0, 0, 0, 150), anchor=ancre)
        d.text(p, l, font=f, fill=(255, 255, 255, 245), anchor=ancre)

base = base_film(photo)

if mode == 'grille':
    g = base.copy().convert('RGBA'); c = calque(); d = ImageDraw.Draw(c)
    for k in range(1, 10):
        x, y = W * k / 10, H * k / 10
        d.line([(x, 0), (x, H)], fill=(255, 255, 0, 150), width=2)
        d.line([(0, y), (W, y)], fill=(255, 255, 0, 150), width=2)
        texte(d, (x, 14), str(k * 10), 22, 'mm', 5)
        texte(d, (16, y), str(k * 10), 22, 'lm', 5)
    Image.alpha_composite(g, c).convert('RGB').save(os.path.join(out, 'G-' + job + '.jpg'), quality=88)
    print('grille ok'); sys.exit(0)

if mode == 'tiers':
    # Style « third bending » : grille des tiers dont une ligne est enfoncee par les pattes
    titre = os.environ.get('TITRE', '').strip()[:60]
    pattes = sorted(json.loads(os.environ.get('PATTES', '[]') or '[]')[:3], key=lambda q: float(q['x']))
    pts = [P(float(q['x']), float(q['y'])) for q in pattes]
    if not pts:
        print('aucune patte'); sys.exit(1)
    ymax = max(q[1] for q in pts)
    yL = H * 2 / 3 if ymax > H * 2 / 3 else H / 3
    base.save(os.path.join(out, 'base.jpg'), quality=92)
    def trait(d, a, b, alpha):
        d.line([(a[0] + 1.5, a[1] + 1.5), (b[0] + 1.5, b[1] + 1.5)], fill=(0, 0, 0, int(70 * alpha)), width=3)
        d.line([a, b], fill=(255, 255, 255, int(230 * alpha)), width=3)
    def grille(prog, alpha):
        c = calque(); d = ImageDraw.Draw(c)
        for k in (1, 2):
            trait(d, (W * k / 3, 0), (W * k / 3, H), alpha)
        for yy in (H / 3, H * 2 / 3):
            if abs(yy - yL) > 1:
                trait(d, (0, yy), (W, yy), alpha)
        eff = [(x, yL + (y - yL) * prog) for (x, y) in pts]
        trait(d, (0, yL), eff[0], alpha)
        trait(d, eff[-1], (W, yL), alpha)
        return c
    def ease(x):
        x = min(max(x, 0.0), 1.0); c1 = 1.70158; c3 = c1 + 1
        return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2
    ct = calque(); d = ImageDraw.Draw(ct)
    if titre:
        texte(d, (56, 92), titre.upper(), 50, 'lm', 24)
    texte(d, (W / 2, H - 44), '@pattepatte2026', 28, 'mm', 40)
    ct.save(os.path.join(out, 'calque_titre.png'))
    os.makedirs(os.path.join(out, 'frames'), exist_ok=True)
    for i in range(40):
        t = i / 15.0
        grille(ease((t - 1.0) / 1.1), min(1.0, t / 0.5)).save(os.path.join(out, 'frames', 'f%03d.png' % i))
    fin = Image.alpha_composite(Image.alpha_composite(base.convert('RGBA'), grille(1.0, 1.0)), ct)
    fin.convert('RGB').save(os.path.join(out, 'A-' + job + '.jpg'), quality=92)
    print('tiers ok', len(pts), 'pattes'); sys.exit(0)

titre = os.environ.get('TITRE', '').strip()[:60]
annots = json.loads(os.environ.get('ANNOTATIONS', '[]') or '[]')[:5]
base.save(os.path.join(out, 'base.jpg'), quality=92)
calques = []
# 1) grille des tiers discrète (clin d'oeil photo)
c = calque(); d = ImageDraw.Draw(c)
for k in (1, 2):
    d.line([(W * k / 3, 0), (W * k / 3, H)], fill=(255, 255, 255, 70), width=2)
    d.line([(0, H * k / 3), (W, H * k / 3)], fill=(255, 255, 255, 70), width=2)
calques.append(c)
# 2) titre + signature
c = calque(); d = ImageDraw.Draw(c)
if titre:
    texte(d, (56, 92), titre.upper(), 50, 'lm', 24)
    ligne(d, (56, 92 + 50 * 0.9 * max(1, len(textwrap.wrap(titre.upper(), 24))) / 1.2 + 26), (300, 92 + 50 * 0.9 * max(1, len(textwrap.wrap(titre.upper(), 24))) / 1.2 + 26), 3)
texte(d, (W / 2, H - 44), '@pattepatte2026', 28, 'mm', 40)
calques.append(c)
# 3) une flèche par annotation
for a in annots:
    x, y = P(float(a['x']), float(a['y']))
    tx, ty = P(float(a.get('tx', a['x'])), float(a.get('ty', a['y'])))
    c = calque(); d = ImageDraw.Draw(c)
    d.ellipse([x - 16, y - 16, x + 16, y + 16], outline=(0, 0, 0, 110), width=4)
    d.ellipse([x - 15, y - 15, x + 15, y + 15], outline=(255, 255, 255, 240), width=3)
    lab = str(a.get('texte', ''))[:60]
    sz = 32; f = font(sz)
    lignes_l = textwrap.wrap(lab, 18) or ['']
    w = max(d.textlength(l, font=f) for l in lignes_l)
    hbloc = sz * 1.18 * len(lignes_l)
    ty = min(max(ty, 150 + hbloc / 2), H - 90 - hbloc / 2)
    droite = tx >= x
    xs = tx + 12 if droite else tx - 12 - w
    xs = min(max(xs, 24), W - 24 - w)
    bout = (xs - 10, ty) if droite else (xs + w + 10, ty)
    v = np.array([bout[0] - x, bout[1] - y]); n = np.linalg.norm(v) or 1
    debut = (x + v[0] / n * 17, y + v[1] / n * 17)
    ligne(d, debut, bout, 3)
    texte(d, (xs, ty), lab, sz, 'lm', 18)
    calques.append(c)
for i, c in enumerate(calques):
    c.save(os.path.join(out, 'calque%d.png' % i))
fin = base.convert('RGBA')
for c in calques:
    fin = Image.alpha_composite(fin, c)
fin.convert('RGB').save(os.path.join(out, 'A-' + job + '.jpg'), quality=92)
print('final ok', len(calques), 'calques')
