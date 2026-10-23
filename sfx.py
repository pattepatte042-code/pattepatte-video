#!/usr/bin/env python3
"""Bruitages originaux Patte a Patte (post-production son, generes, sans droits tiers).
Usage : python3 sfx.py coupes.txt DUREE_S sortie.wav
coupes.txt : une ligne par diapo -> "debut_s type" (couverture / point / fin)
- whoosh doux a chaque changement de diapo
- petit "pop" quand le numero du point apparait
- "ding" leger sur la diapo de fin
"""
import sys, wave
import numpy as np

SR = 44100
coupes = []
for ligne in open(sys.argv[1]):
    p = ligne.split()
    if len(p) >= 2:
        coupes.append((float(p[0]), p[1]))
duree = float(sys.argv[2])
sortie = sys.argv[3]
n = int(SR * (duree + 0.5))
L = np.zeros(n); R = np.zeros(n)
rng = np.random.default_rng(7)

def place(sig, t0, pan=0.0):
    i = int(t0 * SR)
    if i >= n:
        return
    j = min(n, i + len(sig))
    s = sig[: j - i]
    L[i:j] += s * (1 - max(0, pan)); R[i:j] += s * (1 + min(0, pan))

def whoosh(d=0.32):
    t = np.arange(int(SR * d)) / SR
    bruit = rng.normal(0, 1, len(t))
    # filtre passe-bande glissant (montee puis descente) par moyenne mobile variable
    out = np.zeros_like(bruit); acc = 0.0
    for k in range(len(bruit)):
        a = 0.02 + 0.25 * np.sin(np.pi * k / len(bruit))
        acc += a * (bruit[k] - acc); out[k] = acc
    env = np.sin(np.pi * t / d) ** 2
    return out * env * 0.35

def pop(f=880.0, d=0.09):
    t = np.arange(int(SR * d)) / SR
    freq = f * (1.6 - 0.6 * t / d)
    return np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-t * 38) * 0.28

def ding(d=0.9):
    t = np.arange(int(SR * d)) / SR
    s = sum(np.sin(2 * np.pi * f * t) * a for f, a in ((1318.5, 1.0), (1975.5, 0.45), (2637.0, 0.2)))
    return s * np.exp(-t * 5.5) * 0.16

for k, (t0, typ) in enumerate(coupes):
    if k > 0:
        place(whoosh(), max(0, t0 - 0.16), pan=0.3 if k % 2 else -0.3)
    if typ == 'point':
        place(pop(), t0 + 0.12)
    if typ == 'fin':
        place(ding(), t0 + 0.2)

m = max(1e-6, np.max(np.abs(np.concatenate([L, R]))))
g = min(1.0, 0.9 / m)
data = (np.stack([L, R], 1) * g * 32767).astype('<i2')
with wave.open(sortie, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(data.tobytes())
print('sfx ok', len(coupes), 'coupes')
