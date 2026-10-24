#!/usr/bin/env python3
"""Voix off du Reel (Kokoro TTS, Apache 2.0) : une phrase lue par diapo, calee sur le debut de chaque diapo.
Usage : VOIX=am_puck VITESSE=1.05 python3 voix_slides.py spec.json sortie.wav spec_voix.json
Ajoute 'duree' a chaque diapo (assez longue pour la voix) et ecrit la piste voix alignee.
"""
import os, sys, json, re, wave
import numpy as np
from kokoro_onnx import Kokoro

spec = json.load(open(sys.argv[1], encoding='utf-8'))
sortie, sortie_spec = sys.argv[2], sys.argv[3]
SR = 24000
voix = os.environ.get('VOIX', 'am_puck') or 'am_puck'
vit = float(os.environ.get('VITESSE', '1.05') or 1.05)
moteur = Kokoro(os.environ.get('KOKORO_MODELE', 'kokoro-v1.0.onnx'), os.environ.get('KOKORO_VOIX', 'voices-v1.0.bin'))
NUM = ['One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven']

def propre(t):
    t = re.sub(r"[^\w\s\.,!\?'’:;\-]", ' ', str(t or ''))
    return re.sub(r'\s+', ' ', t).strip()

def parler(txt):
    if not txt.strip(' .'):
        return np.zeros(0, np.float32)
    a, sr = moteur.create(txt, voice=voix, speed=vit, lang='en-us')
    a = np.asarray(a, np.float32).reshape(-1)
    if sr != SR:
        x = np.linspace(0, len(a) - 1, int(len(a) * SR / sr))
        a = np.interp(x, np.arange(len(a)), a).astype(np.float32)
    nz = np.where(np.abs(a) > 0.01)[0]
    if len(nz):
        a = a[max(0, nz[0] - int(SR * 0.02)): nz[-1] + int(SR * 0.05)]
    return a

pistes, n = [], 0
for s in spec['slides'][:8]:
    t = s.get('type', 'point')
    if s.get('voix'):
        txt = propre(s['voix'])
    elif t == 'couverture':
        txt = propre(s.get('titre'))
    elif t == 'fin':
        txt = ' '.join(x for x in [propre(s.get('titre')), propre(s.get('question'))] if x)
    else:
        txt = '%s. %s. %s' % (NUM[n] if n < len(NUM) else '', propre(s.get('titre')).rstrip('.'), propre(s.get('texte')))
        n += 1
    a = parler(txt)
    base = 1.6 if t == 'couverture' else (2.6 if t == 'fin' else 2.9)
    debut = 0.1 if t == 'couverture' else 0.3
    d = max(base, debut + len(a) / SR + 0.35)
    s['duree'] = round(d, 2)
    pistes.append((debut, a, d))
    print('%-10s %5.2fs  %s' % (t, d, txt[:70]))

tot = sum(p[2] for p in pistes)
sig = np.zeros(int(SR * (tot + 1.0)), np.float32)
x = 0.0
for debut, a, d in pistes:
    i = int((x + debut) * SR)
    sig[i:i + len(a)] += a[:max(0, len(sig) - i)]
    x += d
sig = sig / max(1e-6, float(np.max(np.abs(sig)))) * 0.92
with wave.open(sortie, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((sig * 32767).astype('<i2').tobytes())
json.dump(spec, open(sortie_spec, 'w', encoding='utf-8'), ensure_ascii=False)
print('voix off ok', round(tot, 2), 's')
