#!/usr/bin/env python3
"""Voix de l animal presentateur (Kokoro TTS, Apache 2.0) + sous-titres mot a mot (ASS).
Usage : TEXTE=... VOIX=am_michael VITESSE=1.0 python3 parle.py sortie_dir
Ecrit voix.wav (24 kHz), mots.json, soustitres.ass, duree.txt
"""
import os, sys, json, re
import wave
import numpy as np

out = sys.argv[1] if len(sys.argv) > 1 else 'tmp/parle'
os.makedirs(out, exist_ok=True)
texte = os.environ.get('TEXTE', '').strip()
voix = os.environ.get('VOIX', 'am_michael')
vitesse = float(os.environ.get('VITESSE', '1.0') or 1.0)
SR = 24000
phrases = [p.strip() for p in re.split(r'\n+|(?<=[.!?])\s+', texte) if p.strip()]

audio, mots, t = [], [], 0.25
audio.append(np.zeros(int(SR * 0.25), dtype=np.float32))
from kokoro_onnx import Kokoro
moteur = Kokoro(os.environ.get('KOKORO_MODELE', 'kokoro-v1.0.onnx'), os.environ.get('KOKORO_VOIX', 'voices-v1.0.bin'))
for ph in phrases:
    a, sr = moteur.create(ph, voice=voix, speed=vitesse, lang='en-us')
    a = np.asarray(a, dtype=np.float32).reshape(-1)
    if sr != SR:
        x = np.linspace(0, len(a) - 1, int(len(a) * SR / sr))
        a = np.interp(x, np.arange(len(a)), a).astype(np.float32)
    # enlever les silences au debut et a la fin de la phrase
    nz = np.where(np.abs(a) > 0.01)[0]
    if len(nz):
        a = a[max(0, nz[0] - int(SR * 0.03)): nz[-1] + int(SR * 0.05)]
    d = len(a) / SR
    # horodatage des mots : reparti selon la longueur (syllabes approx.)
    ws = ph.split()
    poids = [max(1, len(re.findall(r'[aeiouy]+', w.lower()))) + 0.4 for w in ws]
    tot = sum(poids) or 1
    x = t
    for w, pw in zip(ws, poids):
        dd = d * pw / tot
        mots.append({'w': w, 's': round(x, 3), 'e': round(x + dd, 3)}); x += dd
    audio.append(a); t += d
    audio.append(np.zeros(int(SR * 0.22), dtype=np.float32)); t += 0.22
audio.append(np.zeros(int(SR * 0.4), dtype=np.float32)); t += 0.4
sig = np.concatenate(audio)
sig = sig / max(1e-6, float(np.max(np.abs(sig)))) * 0.92
with wave.open(os.path.join(out, 'voix.wav'), 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((sig * 32767).astype('<i2').tobytes())
json.dump(mots, open(os.path.join(out, 'mots.json'), 'w'), ensure_ascii=False)
open(os.path.join(out, 'duree.txt'), 'w').write('%.2f' % t)

# --- sous-titres : groupes de 3 mots, le mot dit est en jaune et grossit ---
def ts(x):
    x = max(0.0, x); h = int(x // 3600); m = int(x % 3600 // 60); s = x % 60
    return '%d:%02d:%05.2f' % (h, m, s)
def propre(w):
    return w.replace('{', '').replace('}', '').replace('\\', '')
ACC = os.environ.get('COULEUR_ASS', '&H0000D7FF')  # jaune (BGR)
lignes = []
groupes, g = [], []
for i, m in enumerate(mots):
    g.append(m)
    fin = m['w'][-1:] in '.!?,' or len(g) == 3
    if fin:
        groupes.append(g); g = []
if g:
    groupes.append(g)
for gi, g in enumerate(groupes):
    fin_g = groupes[gi + 1][0]['s'] if gi + 1 < len(groupes) else g[-1]['e'] + 0.3
    for k, m in enumerate(g):
        deb = m['s']; fin = g[k + 1]['s'] if k + 1 < len(g) else fin_g
        parts = []
        for j, mm in enumerate(g):
            w = propre(mm['w']).upper()
            if j == k:
                parts.append('{\\c%s\\fscx112\\fscy112}%s{\\c&H00FFFFFF&\\fscx100\\fscy100}' % (ACC, w))
            else:
                parts.append(w)
        lignes.append('Dialogue: 0,%s,%s,Mots,,0,0,0,,%s' % (ts(deb), ts(fin), ' '.join(parts)))
ass = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Mots,Poppins,92,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,7,3,2,70,70,560,1
Style: Petit,Poppins,34,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,3,1,8,40,40,60,1
Style: Sign,Poppins,36,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,3,1,2,40,40,120,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
ass += 'Dialogue: 1,0:00:00.00,%s,Petit,,0,0,0,,AI-generated video\n' % ts(t + 1)
ass += 'Dialogue: 1,0:00:00.00,%s,Sign,,0,0,0,,@pattepatte2026\n' % ts(t + 1)
ass += '\n'.join(lignes) + '\n'
open(os.path.join(out, 'soustitres.ass'), 'w', encoding='utf-8').write(ass)
print('voix ok', round(t, 2), 's,', len(mots), 'mots')
