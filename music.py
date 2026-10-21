#!/usr/bin/env python3
"""Musique originale Patte a Patte (generee, sans droits d'auteur tiers).
Usage : python3 music.py DUREE_S GRAINE sortie.wav
Ukulele / harpe douce + basse + petite percussion, style joyeux 'animaux'.
Meme graine = meme musique ; chaque video a sa variante.
"""
import sys, wave, hashlib
import numpy as np

SR = 44100
duree = float(sys.argv[1]) if len(sys.argv) > 1 else 12.0
graine = sys.argv[2] if len(sys.argv) > 2 else 'patte'
sortie = sys.argv[3] if len(sys.argv) > 3 else 'musique.wav'
rng = np.random.default_rng(int(hashlib.sha256(graine.encode()).hexdigest()[:8], 16))

tempo = float(rng.choice([92, 96, 100, 104, 108]))
beat = 60.0 / tempo
tonique = int(rng.choice([60, 62, 65, 67]))  # do, re, fa, sol
progressions = [[0, 7, 9, 5], [0, 9, 5, 7], [9, 5, 0, 7], [0, 5, 9, 7], [5, 7, 0, 0]]
prog = progressions[int(rng.integers(len(progressions)))]
majeur = {0: 'M', 5: 'M', 7: 'M', 9: 'm'}
n = int(SR * (duree + 1.0))
gauche = np.zeros(n); droite = np.zeros(n)

def hz(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)

def pincee(freq, dur, amp, brillance=1.0):
    t = np.arange(int(SR * dur)) / SR
    s = np.zeros_like(t)
    for k in range(1, 9):
        if freq * k > 9000:
            break
        s += (brillance ** (k - 1)) * np.sin(2 * np.pi * freq * k * t + rng.random()) / k * np.exp(-t * (2.2 + 1.6 * k))
    att = np.minimum(1.0, t / 0.004)
    return amp * s * att

def ajoute(sig, debut, pan=0.0):
    i = int(debut * SR)
    if i >= n:
        return
    j = min(n, i + len(sig))
    g = np.sqrt(0.5 * (1 - pan)); d = np.sqrt(0.5 * (1 + pan))
    gauche[i:j] += sig[: j - i] * g
    droite[i:j] += sig[: j - i] * d

def accord(degre):
    racine = tonique + degre - (12 if degre > 7 else 0)
    tierce = 3 if majeur[degre] == 'm' else 4
    return [racine, racine + tierce, racine + 7, racine + 12]

# rythme ukulele : B B H _ H B H (1/8)
motif = [(0, 1.0, 1), (1, 0.55, -1), (1.5, 0.7, -1), (2.5, 0.6, 1), (3, 0.8, -1), (3.5, 0.6, 1)]
gamme = [0, 2, 4, 7, 9, 12, 14, 16]
mesure = 4 * beat
nb_mesures = int(np.ceil(duree / mesure)) + 1
for m in range(nb_mesures):
    t0 = m * mesure
    deg = prog[m % len(prog)]
    notes = accord(deg)
    for (b, a, sens) in motif:
        ordre = notes if sens > 0 else notes[::-1]
        for k, note in enumerate(ordre):
            ajoute(pincee(hz(note), 1.2, 0.07 * a, 0.55), t0 + b * beat + k * 0.012, pan=-0.25)
    # basse sur 1 et 3
    racine = tonique + deg - 24 - (12 if deg > 7 else 0)
    for b in (0, 2):
        t = np.arange(int(SR * beat * 1.6)) / SR
        ajoute(0.22 * np.sin(2 * np.pi * hz(racine) * t) * np.exp(-t * 2.5) * np.minimum(1, t / 0.01), t0 + b * beat)
    # melodie clochette (pentatonique), apparait apres la 1re mesure
    if m >= 1:
        for b in range(8):
            if rng.random() < 0.55:
                note = tonique + 12 + int(rng.choice(gamme))
                ajoute(pincee(hz(note), 0.9, 0.06, 0.25), t0 + b * beat / 2, pan=0.35)
    # percussion : grosse caisse douce + shaker
    for b in range(4):
        t = np.arange(int(SR * 0.25)) / SR
        if b in (0, 2):
            f = 110 * np.exp(-t * 18) + 45
            ajoute(0.35 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 14), t0 + b * beat)
    for b in range(8):
        t = np.arange(int(SR * 0.07)) / SR
        bruit = rng.standard_normal(len(t))
        bruit = np.diff(np.concatenate([[0], bruit]))  # aigus
        ajoute(0.025 * (1.0 if b % 2 else 0.6) * bruit * np.exp(-t * 60), t0 + b * beat / 2, pan=0.2)

stereo = np.stack([gauche, droite], axis=1)[: int(SR * duree)]
# fondu entree/sortie + normalisation douce
lt = len(stereo)
env = np.ones(lt)
fi = int(0.4 * SR); fo = int(1.2 * SR)
env[:fi] = np.linspace(0, 1, fi)
env[-fo:] = np.linspace(1, 0, fo)
stereo *= env[:, None]
stereo = np.tanh(stereo * 1.3)
stereo *= 0.7 / max(1e-6, np.max(np.abs(stereo)))
pcm = (stereo * 32767).astype('<i2')
with wave.open(sortie, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes(pcm.tobytes())
print('musique', sortie, 'tempo', tempo, 'tonique', tonique, 'progression', prog)
