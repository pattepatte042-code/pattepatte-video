#!/usr/bin/env python3
"""Fabrique de carrousels Patte a Patte (1080x1350, fond uni colore, gros chiffres, icones).
Usage : python3 carousel.py spec.json sortie_dir JOB [photo.jpg]
spec = {"theme": "menthe|corail|ciel|soleil|lavande",
        "categorie": "CHIEN",
        "slides": [
          {"type": "couverture", "titre": "...", "titre_en": "...", "emoji": "🐕"},
          {"type": "point", "titre": "...", "texte": "...", "titre_en": "...", "emoji": "📦"},
          {"type": "fin", "titre": "...", "question": "...", "titre_en": "...", "emoji": "💬"}]}
Sortie : C-JOB-1.jpg ... C-JOB-n.jpg
"""
import sys, os, json, textwrap
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter

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

def bloc(d, xy, texte, chemin, sz, larg, couleur, interligne=1.12, max_lignes=6, min_sz=30, dessine=True):
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
            d.text((xy[0], y), l, font=fnt, fill=couleur)
        y += int(sz * interligne)
    return y - xy[1]

def pied(d, i):
    fp = f(F_MED, 26)
    d.text((M, H - 70), '@pattepatte2026', font=fp, fill=DOUX, anchor='lm')
    # points de pagination
    x0 = W - M - (N - 1) * 26
    for k in range(N):
        r = 7 if k == i else 5
        c = ACC if k == i else (*DOUX, )
        d.ellipse([x0 + k * 26 - r, H - 70 - r, x0 + k * 26 + r, H - 70 + r], fill=c if k == i else tuple(int(a * 0.5 + b * 0.5) for a, b in zip(DOUX, FOND)))

def pastille(d, xy, texte, fond, couleur, sz=28, ancre_droite=False):
    fp = f(F_BOLD, sz)
    w = d.textlength(texte, font=fp)
    x, y = xy
    if ancre_droite:
        x = x - w - 44
    d.rounded_rectangle([x, y, x + w + 44, y + sz + 26], radius=(sz + 26) // 2, fill=fond)
    d.text((x + 22, y + (sz + 26) / 2), texte, font=fp, fill=couleur, anchor='lm')
    return x + w + 44

def coller(im, motif, xy):
    if motif is not None:
        im.alpha_composite(motif, (int(xy[0]), int(xy[1])))

def couverture(s, i):
    im = Image.new('RGBA', (W, H), FOND + (255,)); d = ImageDraw.Draw(im)
    pastille(d, (M, 84), str(spec.get('categorie', 'ASTUCE')).upper()[:20], ACC, (255, 255, 255))
    y = 190
    h = bloc(d, (M, y), s.get('titre', ''), F_BOLD, 92, W - 2 * M, TXT, 1.08, max_lignes=4, min_sz=64)
    y += h + 10
    if s.get('titre_en'):
        y += 14 + bloc(d, (M, y + 14), s['titre_en'], F_MED, 38, W - 2 * M, DOUX, 1.2, max_lignes=2) + 10
    # carte photo (ou grand emoji) en bas
    top, bas = max(y + 40, 640), H - 140
    if photo:
        p = Image.open(photo).convert('RGB')
        p = ImageOps.fit(p, (W - 2 * M, bas - top), Image.LANCZOS, centering=(0.5, 0.45)).convert('RGBA')
        masque = Image.new('L', p.size, 0)
        ImageDraw.Draw(masque).rounded_rectangle([0, 0, p.width, p.height], radius=44, fill=255)
        ombre = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(ombre).rounded_rectangle([M + 6, top + 14, W - M + 6, bas + 14], radius=44, fill=(0, 0, 0, 60))
        im.alpha_composite(ombre.filter(ImageFilter.GaussianBlur(16)))
        im.paste(p, (M, top), masque)
        e = emoji_img(s.get('emoji'), 130)
        if e:
            coller(im, e, (W - M - e.width + 20, top - e.height // 2))
    else:
        d.rounded_rectangle([M, top, W - M, bas], radius=44, fill=CARTE)
        e = emoji_img(s.get('emoji') or '🐾', min(380, bas - top - 80))
        if e:
            coller(im, e, ((W - e.width) / 2, top + (bas - top - e.height) / 2))
    d = ImageDraw.Draw(im)
    # bouton « glisse »
    fp = f(F_BOLD, 28); txt = 'Glisse'; w = d.textlength(txt, font=fp)
    x1 = W - M - 24; x0 = x1 - w - 100; y0 = bas - 80
    d.rounded_rectangle([x0, y0, x1, y0 + 58], radius=29, fill=TXT)
    d.text((x0 + 28, y0 + 29), txt, font=fp, fill=(255, 255, 255), anchor='lm')
    ax = x1 - 34; ay = y0 + 29
    d.line([(ax - 26, ay), (ax, ay)], fill=(255, 255, 255), width=5)
    d.polygon([(ax + 6, ay), (ax - 10, ay - 11), (ax - 10, ay + 11)], fill=(255, 255, 255))
    pied(d, i)
    return im

def point(s, i, num):
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

def fin(s, i):
    im = Image.new('RGBA', (W, H), ACC + (255,)); d = ImageDraw.Draw(im)
    e = emoji_img(s.get('emoji') or '💬', 190)
    if e:
        coller(im, e, (M, 150))
    d = ImageDraw.Draw(im)
    y = 400
    y += bloc(d, (M, y), s.get('titre', ''), F_BOLD, 84, W - 2 * M, (255, 255, 255), 1.08, max_lignes=3, min_sz=56) + 20
    if s.get('question'):
        y += bloc(d, (M, y), s['question'], F_MED, 44, W - 2 * M, (255, 255, 255), 1.3, max_lignes=4, min_sz=34) + 10
    if s.get('titre_en'):
        y += bloc(d, (M, y), s['titre_en'], F_REG, 32, W - 2 * M, tuple(int(c * 0.25 + 255 * 0.75) for c in ACC), 1.25, max_lignes=3) + 10
    # boutons d'action
    y = max(y + 40, H - 420)
    for txt in ['💬  Réponds en commentaire', '💾  Enregistre pour plus tard', '📤  Envoie à un ami']:
        lab = txt.split('  ', 1)[1]
        fp = f(F_BOLD, 34)
        d.rounded_rectangle([M, y, W - M, y + 86], radius=43, fill=(255, 255, 255))
        ic = emoji_img(txt.split('  ')[0], 48)
        if ic:
            coller(im, ic, (M + 30, y + 19))
        d = ImageDraw.Draw(im)
        d.text((M + 100, y + 43), lab, font=fp, fill=TXT, anchor='lm')
        y += 104
    d.text((M, H - 70), '@pattepatte2026', font=f(F_MED, 26), fill=(255, 255, 255), anchor='lm')
    return im

num = 0
for i, s in enumerate(slides):
    t = s.get('type', 'point')
    if t == 'couverture':
        im = couverture(s, i)
    elif t == 'fin':
        im = fin(s, i)
    else:
        num += 1
        im = point(s, i, s.get('num', num))
    im.convert('RGB').save(os.path.join(out, 'C-%s-%d.jpg' % (job, i + 1)), quality=92)
print('carrousel ok', N, 'images')
