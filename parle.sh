#!/usr/bin/env bash
# Video "l animal presente le sujet" : clips IA + voix Kokoro + sous-titres mot a mot + musique, -14 LUFS.
set -euo pipefail
[[ "${JOB_ID}" =~ ^[A-Za-z0-9_-]{1,60}$ ]] || { echo "job_id invalide"; exit 1; }
[[ "${CLIPS_JOB}" =~ ^[A-Za-z0-9_-]{1,60}$ ]] || { echo "clips_job invalide"; exit 1; }
[[ "${HAUTEUR:-1.0}" =~ ^[0-9]\.[0-9]{1,2}$ ]] || HAUTEUR=1.0
mkdir -p videos tmp/clips polices "$HOME/.fonts"
for p in Bold Medium; do
  curl -fsSL --retry 4 -o "polices/Poppins-${p}.ttf" "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-${p}.ttf" || true
done
cp polices/*.ttf "$HOME/.fonts/" 2>/dev/null || true; fc-cache -f >/dev/null 2>&1 || true
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  [ -f "$f" ] || curl -fsSL --retry 4 -o "$f" "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/$f"
done
DUREE_MIN="${DUREE_MIN:-11.5}" python3 parle.py tmp/parle
DUREE=$(cat tmp/parle/duree.txt)
gh release download clips-ia -p "IA-${CLIPS_JOB}-c*.mp4" -D tmp/clips --clobber
ls tmp/clips
python3 - "$DUREE" <<'PY'
import sys, glob, subprocess
d = float(sys.argv[1])
cl = sorted(glob.glob('tmp/clips/*.mp4'))
assert cl, 'aucun clip IA'
def dur(f):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', f]).decode().strip() or 3)
L, t, i = [], 0.0, 0
while t < d + 0.5:
    f = cl[i % len(cl)]; L.append("file '%s'" % f.split('/')[-1]); t += dur(f); i += 1
open('tmp/clips/liste.txt', 'w').write('\n'.join(L) + '\n')
print('clips utilises :', len(L))
PY
if python3 music.py "${DUREE}" "${JOB_ID}" tmp/musique.wav; then MUS=(-i tmp/musique.wav); else MUS=(-f lavfi -t "${DUREE}" -i anullsrc=r=44100:cl=stereo); fi
H="${HAUTEUR}"
if [[ "$H" == "1.0" || "$H" == "1.00" ]]; then VFX="aresample=44100"; else VFX="asetrate=24000*${H},aresample=44100,atempo=$(python3 -c "print(round(1/${H},4))")"; fi
FIN=$(python3 -c "print(max(0,${DUREE}-0.6))")
ffmpeg -y -loglevel error -f concat -safe 0 -i tmp/clips/liste.txt -i tmp/parle/voix.wav "${MUS[@]}" \
  -filter_complex "[0:v]scale=1108:1920:flags=lanczos,crop=1080:1920,unsharp=5:5:0.5,eq=saturation=1.08:contrast=1.03,fps=30,ass=tmp/parle/soustitres.ass:fontsdir=polices[v];[1:a]${VFX},pan=stereo|c0=c0|c1=c0,volume=1.0[vo];[2:a]volume=0.13[m];[vo][m]amix=inputs=2:duration=longest:normalize=0,afade=t=out:st=${FIN}:d=0.6,loudnorm=I=-14:TP=-1.5:LRA=11[a]" \
  -map "[v]" -map "[a]" -t "${DUREE}" -c:v libx264 -preset medium -crf 19 -profile:v high -pix_fmt yuv420p -r 30 \
  -c:a aac -b:a 160k -ar 44100 -movflags +faststart "videos/P-${JOB_ID}.mp4"
ffmpeg -y -loglevel error -ss 1.0 -i "videos/P-${JOB_ID}.mp4" -frames:v 1 -q:v 3 "videos/P-${JOB_ID}.jpg"
ls -la videos/
