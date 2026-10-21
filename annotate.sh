#!/usr/bin/env bash
# Format « photo annotée » : MODE=grille (aperçu avec quadrillage) ou MODE=final (image + Reel animé)
set -euo pipefail
[[ "${JOB_ID}" =~ ^[A-Za-z0-9_-]{1,60}$ ]] || { echo "job_id invalide"; exit 1; }
case "${IMAGE_URL}" in
  https://pattepatte.app.n8n.cloud/*|https://pixabay.com/*|https://cdn.pixabay.com/*|https://upload.wikimedia.org/*) ;;
  *) echo "adresse d image refusee"; exit 1;;
esac
[[ "${MODE}" == "grille" || "${MODE}" == "final" ]] || { echo "mode invalide"; exit 1; }
mkdir -p videos tmp
curl -fsSL --retry 5 --retry-delay 4 -A "Mozilla/5.0 (pattepatte)" -o tmp/photo.jpg "${IMAGE_URL}"
python3 annotate.py "${MODE}" tmp/photo.jpg tmp "${JOB_ID}"
if [[ "${MODE}" == "grille" ]]; then cp "tmp/G-${JOB_ID}.jpg" videos/; exit 0; fi
cp "tmp/A-${JOB_ID}.jpg" videos/
N=$(ls tmp/calque*.png | wc -l)
NA=$(( N - 2 ))
DUREE=$(awk "BEGIN{d=1.6+${NA}*1.7+3.2; if(d<8)d=8; print int(d+0.5)}")
FIN=$(awk "BEGIN{print ${DUREE}-0.7}")
if python3 music.py "${DUREE}" "${JOB_ID}" tmp/musique.wav; then AUDIO=(-i tmp/musique.wav); else AUDIO=(-f lavfi -t "${DUREE}" -i anullsrc=r=44100:cl=stereo); fi
ENTREES=(-loop 1 -framerate 30 -t "${DUREE}" -i tmp/base.jpg)
FILTRE="[0:v]split=2[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=40:4,eq=brightness=-0.15[bg];[bg][b]overlay=0:285[v0]"
for i in $(seq 0 $((N - 1))); do
  ENTREES+=(-loop 1 -framerate 30 -t "${DUREE}" -i "tmp/calque${i}.png")
  if (( i == 0 )); then T=0.2; elif (( i == 1 )); then T=0.5; else T=$(awk "BEGIN{print 1.6+(${i}-2)*1.7}"); fi
  FILTRE="${FILTRE};[$((i + 1)):v]format=rgba,fade=t=in:st=${T}:d=0.45:alpha=1[l${i}];[v${i}][l${i}]overlay=0:285[v$((i + 1))]"
done
FILTRE="${FILTRE};[v${N}]fade=t=in:st=0:d=0.4,fade=t=out:st=${FIN}:d=0.7,format=yuv420p[v]"
IA=$(( N + 1 ))
ffmpeg -y -loglevel error "${ENTREES[@]}" "${AUDIO[@]}" -filter_complex "${FILTRE}" \
  -map "[v]" -map "${IA}:a" -t "${DUREE}" -c:v libx264 -preset medium -crf 21 -profile:v high -r 30 \
  -c:a aac -b:a 128k -movflags +faststart "videos/A-${JOB_ID}.mp4"
ls -la videos/
