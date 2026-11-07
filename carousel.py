#!/usr/bin/env python3
"""Fabrique de carrousels Patte a Patte (1080x1350).
Version 2 : la photo de l'animal sert d'ARRIERE-PLAN sur toutes les images
(cadrages differents a chaque image), avec une carte blanche lisible pour le texte.
Sans photo : ancien style (fond uni colore).
Usage : python3 carousel.py spec.json sortie_dir JOB [photo.jpg]
spec = {"theme": "menthe|corail|ciel|soleil|lavande",
        "categorie": "CHIEN",
        "slides": [
          {"type": "couverture", "titre": "...", "titre_en": "...", "emoji": "🐕"},
          {"type": "point", "titre": "...", "texte": "...", "titre_en": "...", "emoji": "📦"},
          {"type": "fin", "titre": "...", "question": "...", "titre_en": "...", "emoji": "💬"}]}
Sortie : C-JOB-1.jpg ... C-JOB-n.jpg
"""
import sys, os, json
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter, ImageEnhance

W, H = 1080, 1350
M = 84  # marge
spec_path, out, job = sys.argv[1], sys.argv[2], sys.argv[3]
photo = sys.argv[4] if len(sys.argv) > 4 and os.path.exists(sys.argv[4]) else None
spec = json.load(open(spec_path, encoding='utf-8'))
os.makedirs(out, exist_ok=True)

DOSSIERS = [os.environ.get('POLICES_DIR', ''), 'polices', '/usr/share/fonts/truetype/google-fonts']
def police(nom):
    for d in DOSSIERS:
        p = os.path.join(d, nom)
        if d and os.path.exists(p):
            return p
    return '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
F_BOLD, F_MED, F_REG = police('Poppins-Bold.ttf'), police('Poppins-Medium.ttf'), police('Poppins-Regular.ttf')
EMOJI = next((p for p in ['/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf'] if os.path.exists(p)), None)
def f(p, sz):
    return ImageFont.truetype(p, sz)

THEMES = {  # fond, carte, accent, texte, texte doux
    'menthe':  ((214, 240, 228), (255, 255, 255), (22, 122, 94), (20, 46, 40), (70, 100, 92)),
    'corail':  ((255, 226, 214), (255, 255, 255), (222, 82, 60), (58, 30, 24), (120, 80, 70)),
    'ciel':    ((218, 234, 252), (255, 255, 255), (36, 99, 200), (20, 36, 66), (80, 98, 130)),
    'soleil':  ((255, 239, 196), (255, 255, 255), (214, 128, 0), (60, 42, 10), (120, 95, 50)),
    'lavande': ((232, 225, 252), (255, 255, 255), (104, 72, 200), (36, 26, 70), (96, 86, 130)),
}
FOND, CARTE, ACC, TXT, DOUX = THEMES.get(spec.get('theme', 'menthe'), THEMES['menthe'])
slides = spec['slides'][:8]
N = len(slides)
BLANC = (255, 255, 255)

PHOTO = None
if photo:
    try:
        PHOTO = ImageOps.exif_transpose(Image.open(photo)).convert('RGB')
    except Exception:
        PHOTO = None

# cadrages differents pour chaque image (centre x, centre y, zoom)
CADRAGES = [(0.5, 0.45, 1.0), (0.3, 0.4, 1.35), (0.7, 0.5, 1.35), (0.5, 0.3, 1.6), (0.35, 0.6, 1.5), (0.65, 0.35, 1.5), (0.5, 0.55, 1.25), (0.5, 0.45, 1.1)]

def fond_photo(i, assombrir=0.0, flou=0):
    """Photo plein cadre (1080x1350) avec un cadrage propre a l'image i."""
    cx, cy, z = CADRAGES[i % len(CADRAGES)]
    p = PHOTO
    if z > 1.0:
        w, h = p.size
        cw, ch = int(w / z), int(h / z)
        x0 = int(min(max(cx * w - cw / 2, 0), w - cw)); y0 = int(min(max(cy * h - ch / 2, 0), h - ch))
        p = p.crop((x0, y0, x0 + cw, y0 + ch))
    p = ImageOps.fit(p, (W, H), Image.LANCZOS, centering=(0.5, 0.45))
    p = ImageEnhance.Color(p).enhance(1.12)
    if flou:
        p = p.filter(ImageFilter.GaussianBlur(flou))
    im = p.convert('RGBA')
    if assombrir:
        im.alpha_composite(Image.new('RGBA', (W, H), (0, 0, 0, int(255 * assombrir))))
    return im

def degrade(im, haut, bas, couleur, a0, a1):
    """Degrade vertical de transparence a0 -> a1 entre haut et bas."""
    g = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(g)
    for y in range(int(haut), int(bas)):
        a = a0 + (a1 - a0) * (y - haut) / max(1, bas - haut)
        d.line([(0, y), (W, y)], fill=couleur + (int(a),))
    im.alpha_composite(g)

def emoji_img(ch, taille):
    if not EMOJI or not ch:
        return None
    try:
        fe = ImageFont.truetype(EMOJI, 109)
        im = Image.new('RGBA', (160, 160), (0, 0, 0, 0))
        ImageDraw.Draw(im).text((80, 80), ch, font=fe, embedded_color=True, anchor='mm')
        bb = im.getbbox()
        if not bb:
            return None
        im = im.crop(bb)
        r = taille / max(im.size)
        return im.resize((max(1, int(im.width * r)), max(1, int(im.height * r))), Image.LANCZOS)
    except Exception:
        return None

def wrap_px(d, texte, fnt, larg):
    mots, lignes, cur = str(texte).split(), [], ''
    for m in mots:
        essai = (cur + ' ' + m).strip()
        if d.textlength(essai, font=fnt) <= larg or not cur:
            cur = essai
        else:
            lignes.append(cur); cur = m
    if cur:
        lignes.append(cur)
    return lignes

def bloc(d, xy, texte, chemin, sz, larg, couleur, interligne=1.12, max_lignes=6, min_sz=30, dessine=True, ombre=False):
    """Ecrit un paragraphe ; reduit la taille si trop de lignes. Retourne la hauteur utilisee."""
    while True:
        fnt = f(chemin, sz)
        lignes = wrap_px(d, texte, fnt, larg)
        if len(lignes) <= max_lignes or sz <= min_sz:
            break
        sz -= 4
    y = xy[1]
    for l in lignes[:max_lignes]:
        if dessine:
            if ombre:
                d.text((xy[0] + 3, y + 3), l, font=fnt, fill=(0, 0, 0, 150))
            d.text((xy[0], y), l, font=fnt, fill=couleur)
        y += int(sz * interligne)
    return y - xy[1]

def pied(d, i, couleur=None, fond_points=None):
    couleur = couleur or DOUX
    fp = f(F_MED, 26)
    d.text((M, H - 70), '@pattepatte2026', font=fp, fill=couleur, anchor='lm')
    x0 = W - M - (N - 1) * 26
    for k in range(N):
        r = 7 if k == i else 5
        inactif = fond_points or tuple(int(a * 0.5 + b * 0.5) for a, b in zip(DOUX, FOND))
        d.ellipse([x0 + k * 26 - r, H - 70 - r, x0 + k * 26 + r, H - 70 + r], fill=ACC if k == i else inactif)

def pastille(d, xy, texte, fond, couleur, sz=28):
    fp = f(F_BOLD, sz)
    w = d.textlength(texte, font=fp)
    x, y = xy
    d.rounded_rectangle([x, y, x + w + 44, y + sz + 26], radius=(sz + 26) // 2, fill=fond)
    d.text((x + 22, y + (sz + 26) / 2), texte, font=fp, fill=couleur, anchor='lm')
    return x + w + 44

def coller(im, motif, xy):
    if motif is not None:
        im.alpha_composite(motif, (int(xy[0]), int(xy[1])))

def bouton_glisse(d, x1, y0):
    fp = f(F_BOLD, 28); txt = 'Swipe'; w = d.textlength(txt, font=fp)
    x0 = x1 - w - 100
    d.rounded_rectangle([x0, y0, x1, y0 + 58], radius=29, fill=ACC)
    d.text((x0 + 28, y0 + 29), txt, font=fp, fill=BLANC, anchor='lm')
    ax = x1 - 34; ay = y0 + 29
    d.line([(ax - 26, ay), (ax, ay)], fill=BLANC, width=5)
    d.polygon([(ax + 6, ay), (ax - 10, ay - 11), (ax - 10, ay + 11)], fill=BLANC)

# ---------- avec photo en arriere-plan ----------
def couverture_photo(s, i):
    im = fond_photo(i)
    degrade(im, H * 0.42, H, (0, 0, 0), 0, 215)
    degrade(im, 0, 260, (0, 0, 0), 110, 0)
    d = ImageDraw.Draw(im)
    pastille(d, (M, 84), str(spec.get('categorie', 'ASTUCE')).upper()[:20], ACC, BLANC)
    larg = W - 2 * M
    h_titre = bloc(d, (M, 0), s.get('titre', ''), F_BOLD, 96, larg, BLANC, 1.06, 4, 64, dessine=False)
    h_en = bloc(d, (M, 0), s['titre_en'], F_MED, 38, larg, BLANC, 1.2, 2, dessine=False) + 14 if s.get('titre_en') else 0
    y = H - 170 - h_en - h_titre
    bloc(d, (M, y), s.get('titre', ''), F_BOLD, 96, larg, BLANC, 1.06, 4, 64, ombre=True)
    if s.get('titre_en'):
        bloc(d, (M, y + h_titre + 14), s['titre_en'], F_MED, 38, larg, (235, 235, 235), 1.2, 2, ombre=True)
    e = emoji_img(s.get('emoji'), 120)
    if e:
        coller(im, e, (W - M - e.width, 70))
    d = ImageDraw.Draw(im)
    bouton_glisse(d, W - M, H - 150)
    pied(d, i, BLANC, (200, 200, 200))
    return im

def point_photo(s, i, num):
    im = fond_photo(i, assombrir=0.08)
    d = ImageDraw.Draw(im)
    larg = W - 2 * M - 60; x = M + 30
    def pile(dessine, y0, dd):
        y = y0
        y += bloc(dd, (x, y), s.get('titre', ''), F_BOLD, 70, larg - 150, TXT, 1.1, 3, 50, dessine) + 12
        if s.get('titre_en'):
            y += bloc(dd, (x, y), s['titre_en'], F_MED, 34, larg, ACC, 1.2, 2, 28, dessine) + 6
        if dessine:
            dd.line([(x, y + 18), (x + 120, y + 18)], fill=ACC, width=7)
        y += 50
        y += bloc(dd, (x, y), s.get('texte', ''), F_REG, 44, larg, DOUX, 1.36, 6, 32, dessine)
        return y - y0
    h = pile(False, 0, d)
    bas = H - 120
    haut = bas - h - 74 - 26 - 56
    # carte blanche legerement transparente en bas, la photo reste visible en haut
    carte = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(carte).rounded_rectangle([M - 30, haut + 10, W - M + 30, bas + 10], radius=48, fill=(0, 0, 0, 70))
    im.alpha_composite(carte.filter(ImageFilter.GaussianBlur(18)))
    carte = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(carte).rounded_rectangle([M - 30, haut, W - M + 30, bas], radius=48, fill=CARTE + (243,))
    im.alpha_composite(carte)
    d = ImageDraw.Draw(im)
    # pastille ronde avec le numero, a cheval sur la carte
    r = 74; cx, cy = M + 30 + r, haut
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ACC, outline=BLANC, width=8)
    d.text((cx, cy + 4), str(num), font=f(F_BOLD, 96), fill=BLANC, anchor='mm')
    pile(True, haut + r + 26, d)
    e = emoji_img(s.get('emoji'), 120)
    if e:
        coller(im, e, (W - M - e.width, haut + 30))
    d = ImageDraw.Draw(im)
    # bandeau pied lisible sur la photo
    degrade(im, H - 110, H, (0, 0, 0), 0, 150)
    pied(ImageDraw.Draw(im), i, BLANC, (200, 200, 200))
    return im

def fin_photo(s, i):
    im = fond_photo(i, flou=6)
    im.alpha_composite(Image.new('RGBA', (W, H), ACC + (178,)))
    return fin_contenu(im, s, i)

# ---------- sans photo (ancien style) ----------
def couverture_uni(s, i):
    im = Image.new('RGBA', (W, H), FOND + (255,)); d = ImageDraw.Draw(im)
    pastille(d, (M, 84), str(spec.get('categorie', 'ASTUCE')).upper()[:20], ACC, BLANC)
    y = 190
    y += bloc(d, (M, y), s.get('titre', ''), F_BOLD, 92, W - 2 * M, TXT, 1.08, 4, 64) + 10
    if s.get('titre_en'):
        y += 14 + bloc(d, (M, y + 14), s['titre_en'], F_MED, 38, W - 2 * M, DOUX, 1.2, 2) + 10
    top, bas = max(y + 40, 640), H - 140
    d.rounded_rectangle([M, top, W - M, bas], radius=44, fill=CARTE)
    e = emoji_img(s.get('emoji') or '🐾', min(380, bas - top - 80))
    if e:
        coller(im, e, ((W - e.width) / 2, top + (bas - top - e.height) / 2))
    d = ImageDraw.Draw(im)
    bouton_glisse(d, W - M - 24, bas - 80)
    pied(d, i)
    return im

def point_uni(s, i, num):
    im = Image.new('RGBA', (W, H), FOND + (255,)); d = ImageDraw.Draw(im)
    haut, bas = 120, H - 130
    d.rounded_rectangle([M - 20, haut, W - M + 20, bas], radius=48, fill=CARTE)
    larg = W - 2 * M - 60; x = M + 30
    def pile(dessine, y0):
        y = y0
        if dessine:
            d.text((x - 6, y - 70), str(num), font=f(F_BOLD, 300), fill=ACC)
        y += 290
        y += bloc(d, (x, y), s.get('titre', ''), F_BOLD, 76, larg, TXT, 1.1, 3, 52, dessine) + 14
        if s.get('titre_en'):
            y += bloc(d, (x, y), s['titre_en'], F_MED, 36, larg, ACC, 1.2, 2, 28, dessine) + 8
        if dessine:
            d.line([(x, y + 22), (x + 140, y + 22)], fill=ACC, width=7)
        y += 62
        y += bloc(d, (x, y), s.get('texte', ''), F_REG, 48, larg, DOUX, 1.38, 7, 32, dessine)
        return y - y0
    h = pile(False, 0)
    y0 = haut + max(60, (bas - haut - h) / 2)
    pile(True, y0)
    e = emoji_img(s.get('emoji'), 200)
    if e:
        coller(im, e, (W - M - 20 - e.width, y0 + 20))
    pied(ImageDraw.Draw(im), i)
    return im

def fin_uni(s, i):
    return fin_contenu(Image.new('RGBA', (W, H), ACC + (255,)), s, i)

def fin_contenu(im, s, i):
    e = emoji_img(s.get('emoji') or '💬', 190)
    if e:
        coller(im, e, (M, 150))
    d = ImageDraw.Draw(im)
    y = 400
    y += bloc(d, (M, y), s.get('titre', ''), F_BOLD, 84, W - 2 * M, BLANC, 1.08, 3, 56) + 20
    if s.get('question'):
        y += bloc(d, (M, y), s['question'], F_MED, 44, W - 2 * M, BLANC, 1.3, 4, 34) + 10
    if s.get('titre_en'):
        y += bloc(d, (M, y), s['titre_en'], F_REG, 32, W - 2 * M, tuple(int(c * 0.25 + 255 * 0.75) for c in ACC), 1.25, 3) + 10
    y = max(y + 40, H - 420)
    for txt in ['💬  Answer in the comments', '💾  Save it for later', '📤  Send it to a friend']:
        lab = txt.split('  ', 1)[1]
        fp = f(F_BOLD, 34)
        d.rounded_rectangle([M, y, W - M, y + 86], radius=43, fill=BLANC)
        ic = emoji_img(txt.split('  ')[0], 48)
        if ic:
            coller(im, ic, (M + 30, y + 19))
        d = ImageDraw.Draw(im)
        d.text((M + 100, y + 43), lab, font=fp, fill=TXT, anchor='lm')
        y += 104
    d.text((M, H - 70), '@pattepatte2026', font=f(F_MED, 26), fill=BLANC, anchor='lm')
    return im

num = 0
for i, s in enumerate(slides):
    t = s.get('type', 'point')
    if t == 'couverture':
        im = couverture_photo(s, i) if PHOTO else couverture_uni(s, i)
    elif t == 'fin':
        im = fin_photo(s, i) if PHOTO else fin_uni(s, i)
    else:
        num += 1
        n = s.get('num', num)
        im = point_photo(s, i, n) if PHOTO else point_uni(s, i, n)
    im.convert('RGB').save(os.path.join(out, 'C-%s-%d.jpg' % (job, i + 1)), quality=92)
print('carrousel ok', N, 'images', 'photo' if PHOTO else 'sans photo')
