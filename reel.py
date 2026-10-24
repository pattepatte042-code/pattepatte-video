#!/usr/bin/env python3
"""Reel educatif anime Patte a Patte (1080x1920, 30 i/s), design propre au Reel.
Toute l'information est montree A L'ECRAN, en animation (accroche, points, question finale).
Usage : python3 reel.py spec.json photo.jpg sortie_frames_dir
spec = meme format que le carrousel : theme, categorie, slides[couverture|point|fin]
Ecrit des images f00000.png ... et duree.txt (secondes).
"""
import sys, os, json, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageEnhance

W, H, FPS = 1080, 1920, 30
spec = json.load(open(sys.argv[1], encoding='utf-8'))
photo_path = sys.argv[2] if len(sys.argv) > 2 and os.path.exists(sys.argv[2]) else None
out = sys.argv[3] if len(sys.argv) > 3 else 'frames'
os.makedirs(out, exist_ok=True)

DOSSIERS = [os.environ.get('POLICES_DIR', ''), 'polices', '/usr/share/fonts/truetype/google-fonts']
def police(nom):
    for d in DOSSIERS:
        p = os.path.join(d, nom)
        if d and os.path.exists(p):
            return p
    return '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
F_BOLD, F_MED, F_REG = police('Poppins-Bold.ttf'), police('Poppins-Medium.ttf'), police('Poppins-Regular.ttf')
EMOJI = '/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf' if os.path.exists('/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf') else None
_fc = {}
def f(p, s):
    k = (p, s)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(p, s)
    return _fc[k]

THEMES = {
    'menthe':  ((22, 122, 94), (214, 240, 228)),
    'corail':  ((222, 82, 60), (255, 226, 214)),
    'ciel':    ((36, 99, 200), (218, 234, 252)),
    'soleil':  ((214, 128, 0), (255, 239, 196)),
    'lavande': ((104, 72, 200), (232, 225, 252)),
}
ACC, PALE = THEMES.get(spec.get('theme', 'menthe'), THEMES['menthe'])
BLANC, NOIR = (255, 255, 255), (22, 22, 28)
slides = spec['slides'][:8]

def ease_out(x):
    x = min(max(x, 0.0), 1.0); return 1 - (1 - x) ** 3
def ease_back(x):
    x = min(max(x, 0.0), 1.0); c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2

_ec = {}
def emoji(ch, taille):
    if not EMOJI or not ch:
        return None
    k = (ch, taille)
    if k in _ec:
        return _ec[k]
    try:
        fe = ImageFont.truetype(EMOJI, 109)
        im = Image.new('RGBA', (170, 170), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((85, 85), ch, font=fe, embedded_color=True, anchor='mm')
        bb = im.getbbox()
        im = im.crop(bb) if bb else None
        if im is not None:
            r = taille / max(im.size)
            im = im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)
        _ec[k] = im
        return im
    except Exception:
        return None

def wrap(d, txt, fnt, larg):
    mots, lignes, cur = str(txt).split(), [], ''
    for m in mots:
        e = (cur + ' ' + m).strip()
        if d.textlength(e, font=fnt) <= larg or not cur:
            cur = e
        else:
            lignes.append(cur); cur = m
    if cur:
        lignes.append(cur)
    return lignes

def ajuste(d, txt, chemin, sz, larg, maxl, mini):
    while True:
        fnt = f(chemin, sz); l = wrap(d, txt, fnt, larg)
        if len(l) <= maxl or sz <= mini:
            return fnt, l[:maxl], sz
        sz -= 4

# --- fonds ---
if photo_path:
    ph = Image.open(photo_path).convert('RGB')
else:
    ph = Image.new('RGB', (W, H), PALE)
ph = ImageEnhance.Contrast(ImageEnhance.Color(ph).enhance(1.25)).enhance(1.06)
ph = ImageEnhance.Sharpness(ph).enhance(1.3)
# etalonnage chaud et lumineux (post-production image)
_r, _g, _b = ph.split()
ph = Image.merge('RGB', (_r.point(lambda v: min(255, int(v * 1.05 + 4))), _g.point(lambda v: min(255, int(v * 1.01 + 2))), _b.point(lambda v: int(v * 0.95))))
grand = ImageOps.fit(ph, (int(W * 1.15), int(H * 1.15)), Image.LANCZOS, centering=(0.5, 0.42))
flou = ImageOps.fit(ph, (W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(28))
flou = ImageEnhance.Brightness(flou).enhance(0.55)
teinte = Image.new('RGB', (W, H), ACC)
fond_points = Image.blend(flou, teinte, 0.35)
degrade = Image.new('L', (1, H))
for y in range(H):
    degrade.putpixel((0, y), int(255 * max(0, (y - H * 0.5) / (H * 0.5)) ** 1.5 * 0.7))
degrade = degrade.resize((W, H))
degrade_clip = degrade.point(lambda v: int(v * 0.35))
noir = Image.new('RGB', (W, H), (8, 8, 12))

# --- clips video de fond (vraies videos d animaux, une par scene) ---
CLIPS = []
_cd = os.environ.get('CLIPS_DIR', '')
if _cd and os.path.isdir(_cd):
    for _nom in sorted(os.listdir(_cd)):
        _p = os.path.join(_cd, _nom)
        if os.path.isdir(_p):
            _fr = sorted(x for x in os.listdir(_p) if x.endswith('.jpg'))
            if len(_fr) >= 15:
                CLIPS.append((_p, _fr))
LUT = [min(255, int(v * 1.05 + 4)) for v in range(256)] + [min(255, int(v * 1.01 + 2)) for v in range(256)] + [int(v * 0.95) for v in range(256)]
def image_clip(k, t):
    p, fr = CLIPS[k % len(CLIPS)]
    L = len(fr); i = int(t * FPS) % (2 * L - 2)
    if i >= L:
        i = 2 * L - 2 - i
    im = Image.open(os.path.join(p, fr[i])).convert('RGB')
    if im.size != (W, H):
        im = ImageOps.fit(im, (W, H), Image.BILINEAR)
    return ImageEnhance.Color(im).enhance(1.15).point(LUT)
def zoom_centre(im, z):
    cw, ch = int(W / z), int(H / z)
    x0, y0 = (W - cw) // 2, (H - ch) // 2
    return im.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.BILINEAR)

D0 = ImageDraw.Draw(Image.new('RGB', (10, 10)))
frames = []

def carte_arrondie(im, box, fill, r=48, ombre=True):
    if ombre:
        o = Image.new('RGBA', im.size, (0, 0, 0, 0))
        ImageDraw.Draw(o).rounded_rectangle([box[0] + 8, box[1] + 18, box[2] + 8, box[3] + 18], radius=r, fill=(0, 0, 0, 90))
        im.alpha_composite(o.filter(ImageFilter.GaussianBlur(18)))
    ImageDraw.Draw(im).rounded_rectangle(box, radius=r, fill=fill)

def barre_progression(d, prog):
    d.rounded_rectangle([60, 120, W - 60, 132], radius=6, fill=(255, 255, 255, 90))
    d.rounded_rectangle([60, 120, 60 + int((W - 120) * prog), 132], radius=6, fill=BLANC)

def signature(d, a=255):
    d.text((W // 2, H - 250), '@pattepatte2026', font=f(F_MED, 34), fill=(255, 255, 255, a), anchor='mm')

TOTAL = 0.0
plan = []
for s in slides:
    t = s.get('type', 'point')
    dur = float(s['duree']) if s.get('duree') else (1.6 if t == 'couverture' else (2.6 if t == 'fin' else 2.9))
    plan.append((s, t, TOTAL, dur)); TOTAL += dur

def scene_couverture(s, t_reel, d_s, prog_global):
    z = 1.0 + 0.22 * (1 - ease_out(t_reel / 0.45)) + 0.06 * (t_reel / d_s)  # zoom choc au debut
    t = t_reel + 1.7  # accroche visible des la 1re image
    if CLIPS:
        bg = zoom_centre(image_clip(0, t_reel), z)
    else:
        cw, ch = int(W * 1.15 / z * 1.0), int(H * 1.15 / z * 1.0)
        x0 = (grand.width - cw) // 2; y0 = (grand.height - ch) // 2
        bg = grand.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.LANCZOS)
    im = Image.composite(noir, bg, degrade_clip if CLIPS else degrade).convert('RGBA')
    d = ImageDraw.Draw(im)
    barre_progression(d, prog_global)
    # pastille categorie
    a = ease_out(t / 0.4)
    cat = str(spec.get('categorie', '')).upper()[:22]
    if cat:
        fp = f(F_BOLD, 34); w = d.textlength(cat, font=fp)
        y = 190 - int(30 * (1 - a))
        d.rounded_rectangle([60, y, 60 + w + 56, y + 68], radius=34, fill=ACC + (int(255 * a),))
        d.text((88, y + 34), cat, font=fp, fill=(255, 255, 255, int(255 * a)), anchor='lm')
    # titre mot par mot
    fnt, lignes, sz = ajuste(d, s.get('titre', ''), F_BOLD, 104, W - 180, 4, 70)
    hl = int(sz * 1.25); ytop = 1200 - hl * len(lignes)
    k = 0
    k0 = 0
    for i, l in enumerate(lignes):
        dt0 = t - 0.35 - 0.12 * k0
        if dt0 > 0:
            eb0 = ease_out(dt0 / 0.3)
            wl = d.textlength(l, font=fnt)
            d.rounded_rectangle([46, ytop + i * hl - 8, 46 + int((wl + 48) * eb0), ytop + i * hl + int(sz * 1.14)], radius=24, fill=ACC + (255,))
        k0 += len(l.split(' '))
    for i, l in enumerate(lignes):
        x = 70
        for mot in l.split(' '):
            dt = t - 0.35 - 0.12 * k; k += 1
            if dt > 0:
                e = ease_back(dt / 0.35)
                yy = ytop + i * hl + int(14 * (1 - e))
                al = int(255 * min(1, dt / 0.2))
                d.text((x, yy), mot, font=fnt, fill=(255, 255, 255, al))
            x += d.textlength(mot + ' ', font=fnt)
    if s.get('titre_en') and t > 1.2:
        al = int(255 * ease_out((t - 1.2) / 0.4))
        fe, le, _ = ajuste(d, s['titre_en'], F_MED, 44, W - 140, 2, 34)
        for i, l in enumerate(le):
            wl = d.textlength(l, font=fe)
            d.rounded_rectangle([56, 1236 + i * 66, 88 + wl, 1236 + i * 66 + 58], radius=18, fill=(255, 255, 255, al))
            d.text((72, 1240 + i * 66), l, font=fe, fill=ACC + (al,))
    e = emoji(s.get('emoji'), 150)
    if e and t > 0.9:
        sc = ease_back((t - 0.9) / 0.45)
        if sc > 0.05:
            ee = e.resize((max(1, int(e.width * sc)), max(1, int(e.height * sc))), Image.LANCZOS)
            im.alpha_composite(ee, (W - 90 - ee.width, ytop - 40 - ee.height))
    signature(d)
    return im

def fond_photo(tt, sombre, clip=None, t_loc=0.0):
    if CLIPS and clip is not None:
        bg = zoom_centre(image_clip(clip, t_loc), 1.0 + 0.05 * min(1.0, t_loc / 3.0))
        return ImageEnhance.Brightness(bg).enhance(sombre).convert('RGBA')
    z = 1.0 + 0.12 * (tt / TOTAL)
    cw, ch = int(W * 1.15 / z), int(H * 1.15 / z)
    x0 = (grand.width - cw) // 2 + int(30 * math.sin(tt * 0.6)); y0 = (grand.height - ch) // 2
    x0 = min(max(x0, 0), grand.width - cw)
    bg = grand.crop((x0, y0, x0 + cw, y0 + ch)).resize((W, H), Image.BILINEAR)
    bg = ImageEnhance.Brightness(bg).enhance(sombre)
    return bg.convert('RGBA')

def ombre_texte(d, xy, txt, fnt, fill, a):
    for ox, oy in ((4, 5), (2, 3)):
        d.text((xy[0] + ox, xy[1] + oy), txt, font=fnt, fill=(0, 0, 0, int(a * 0.55)))
    d.text(xy, txt, font=fnt, fill=fill[:3] + (a,))

def scene_point(s, t_reel, d_s, num, prog_global, tt):
    t = t_reel * 1.8 + 0.2  # animations rapides
    im = fond_photo(tt, 1.0, num, t_reel)
    d = ImageDraw.Draw(im)
    barre_progression(d, prog_global)
    x = 80
    top = 230 if CLIPS else 430
    # pastille numero (cercle couleur) qui « pop »
    eb = ease_back(t / 0.45)
    r = int(105 * max(0.05, eb))
    cx, cy = x + 105, top + 105
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ACC + (255,))
    if eb > 0.3:
        d.text((cx, cy + 6), str(num), font=f(F_BOLD, int(150 * min(1, eb))), fill=BLANC, anchor='mm')
    em = emoji(s.get('emoji'), 190)
    if em and t > 0.35:
        sc = ease_back((t - 0.35) / 0.45)
        if sc > 0.05:
            ee = em.resize((max(1, int(em.width * sc)), max(1, int(em.height * sc))), Image.LANCZOS)
            im.alpha_composite(ee, (W - 90 - ee.width, top + 10))
    d = ImageDraw.Draw(im)
    y = top + 270
    if t > 0.5:
        a = int(255 * ease_out((t - 0.5) / 0.35))
        ft, lt, szt = ajuste(d, s.get('titre', ''), F_BOLD, 112, W - 160, 3, 70)
        dx = int(60 * (1 - a / 255))
        hlt = int(szt * 1.22)
        for i, l in enumerate(lt):
            w = d.textlength(l, font=ft)
            yy = y + i * hlt
            d.rounded_rectangle([x - 24 + dx, yy - 8, x + w + 24 + dx, yy + int(szt * 1.12)], radius=22, fill=ACC + (a,))
            d.text((x + dx, yy), l, font=ft, fill=(255, 255, 255, a))
        y += len(lt) * hlt + 14
        if s.get('titre_en'):
            fe, le, sze = ajuste(d, s['titre_en'], F_BOLD, 44, W - 200, 2, 34)
            for i, l in enumerate(le):
                w = d.textlength(l, font=fe)
                yy = y + i * int(sze * 1.5)
                d.rounded_rectangle([x - 16, yy - 6, x + w + 16, yy + int(sze * 1.3)], radius=18, fill=(255, 255, 255, a))
                d.text((x, yy), l, font=fe, fill=ACC + (a,))
            y += len(le) * int(sze * 1.5)
        y += 34
    if t > 0.95:
        fb, lb, szb = ajuste(d, s.get('texte', ''), F_MED, 56, W - 240, 6, 40)
        hl = int(szb * 1.36)
        a0 = ease_out((t - 0.95) / 0.3)
        boite = Image.new('RGBA', im.size, (0, 0, 0, 0))
        ImageDraw.Draw(boite).rounded_rectangle([x - 20, y - 10, W - 60, y + hl * len(lb) + 40], radius=36, fill=(255, 255, 255, int(235 * a0)))
        im.alpha_composite(boite)
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([x - 20, y - 10, x - 6, y + hl * len(lb) + 40], radius=7, fill=ACC + (int(255 * a0),))
        for i, l in enumerate(lb):
            dt = t - 1.05 - 0.2 * i
            if dt > 0:
                a = ease_out(dt / 0.3)
                d.text((x + 30, y + 22 + i * hl + int(18 * (1 - a))), l, font=fb, fill=(28, 28, 36, int(255 * a)))
    signature(d)
    return im

def scene_fin(s, t_reel, d_s, prog_global):
    t = t_reel * 1.7 + 0.3
    im = Image.new('RGBA', (W, H), ACC + (255,))
    d = ImageDraw.Draw(im)
    barre_progression(d, prog_global)
    em = emoji(s.get('emoji') or '💬', 220)
    if em:
        sc = ease_back(t / 0.5); bob = int(12 * math.sin(t * 5))
        if sc > 0.05:
            ee = em.resize((max(1, int(em.width * sc)), max(1, int(em.height * sc))), Image.LANCZOS)
            im.alpha_composite(ee, ((W - ee.width) // 2, 330 + bob))
    d = ImageDraw.Draw(im)
    a = ease_out((t - 0.25) / 0.4)
    ft, lt, szt = ajuste(d, s.get('titre', ''), F_BOLD, 110, W - 160, 2, 70)
    y = 640
    for i, l in enumerate(lt):
        d.text((W // 2, y + i * int(szt * 1.08) + int(30 * (1 - a))), l, font=ft, fill=(255, 255, 255, int(255 * a)), anchor='ma')
    y += len(lt) * int(szt * 1.08) + 30
    if s.get('question') and t > 0.6:
        a2 = ease_out((t - 0.6) / 0.4)
        fq, lq, szq = ajuste(d, s['question'], F_MED, 56, W - 180, 4, 40)
        for i, l in enumerate(lq):
            d.text((W // 2, y + i * int(szq * 1.3)), l, font=fq, fill=(255, 255, 255, int(255 * a2)), anchor='ma')
        y += len(lq) * int(szq * 1.3) + 20
    if s.get('titre_en') and t > 0.9:
        a3 = ease_out((t - 0.9) / 0.4)
        fe, le, sze = ajuste(d, s['titre_en'], F_REG, 38, W - 180, 2, 30)
        for i, l in enumerate(le):
            d.text((W // 2, y + i * int(sze * 1.25)), l, font=fe, fill=PALE + (int(255 * a3),), anchor='ma')
    yb = 1180
    for k, (ic, lab) in enumerate([('💬', 'Answer in the comments'), ('💾', 'Save it for later'), ('📤', 'Send it to a friend')]):
        dt = t - 1.2 - 0.25 * k
        if dt > 0:
            e = ease_back(dt / 0.4)
            x0 = 120 + int((1 - e) * -700)
            d.rounded_rectangle([x0, yb, x0 + W - 240, yb + 110], radius=55, fill=(255, 255, 255, 255))
            ie = emoji(ic, 60)
            if ie:
                im.alpha_composite(ie, (x0 + 40, yb + 25))
                d = ImageDraw.Draw(im)
            d.text((x0 + 130, yb + 55), lab, font=f(F_BOLD, 42), fill=NOIR, anchor='lm')
        yb += 135
    signature(d)
    return im

n = int(TOTAL * FPS)
num = 0
for fi in range(n):
    tt = fi / FPS
    for (s, typ, debut, dur) in plan:
        if debut <= tt < debut + dur:
            break
    t = tt - debut
    pg = tt / TOTAL
    if typ == 'couverture':
        im = scene_couverture(s, t, dur, pg)
    elif typ == 'fin':
        im = scene_fin(s, t, dur, pg)
    else:
        idx = [p[0] for p in plan if p[1] == 'point'].index(s) + 1
        im = scene_point(s, t, dur, idx, pg, tt)
    im.convert('RGB').save(os.path.join(out, 'f%05d.jpg' % fi), quality=90)
open(os.path.join(out, 'duree.txt'), 'w').write('%.2f' % TOTAL)
open(os.path.join(out, 'coupes.txt'), 'w').write(''.join('%.3f %s\n' % (p[2], p[1]) for p in plan))
print('reel ok', n, 'images', TOTAL, 's')
