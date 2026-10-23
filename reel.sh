#!/usr/bin/env bash
# Reel educatif anime (1080x1920) : toute l'information a l'ecran, photo vive, musique originale
set -euo pipefail
[[ "${JOB_ID}" =~ ^[A-Za-z0-9_-]{1,60}$ ]] || { echo "job_id invalide"; exit 1; }
mkdir -p videos tmp polices tmp/frames
for p in Bold Medium Regular; do
  curl -fsSL --retry 4 -o "polices/Poppins-${p}.ttf" "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-${p}.ttf" || true
done
printf '%s' "${SPEC}" > tmp/spec.json
python3 -c "import json;json.load(open('tmp/spec.json'))" || { echo "spec JSON invalide"; exit 1; }
PHOTO=""
if [[ -n "${IMAGE_URL:-}" ]]; then
  case "${IMAGE_URL}" in
    https://pattepatte.app.n8n.cloud/*|https://pixabay.com/*|https://cdn.pixabay.com/*|https://upload.wikimedia.org/*)
      curl -fsSL --retry 5 --retry-delay 4 -A "Mozilla/5.0 (pattepatte)" -o tmp/photo.jpg "${IMAGE_URL}" && PHOTO=tmp/photo.jpg || PHOTO="";;
    *) echo "adresse d image refusee";;
  esac
fi
POLICES_DIR=polices python3 reel.py tmp/spec.json "${PHOTO:-aucune}" tmp/frames
DUREE=$(cat tmp/frames/duree.txt)
if python3 music.py "${DUREE}" "${JOB_ID}" tmp/musique.wav; then AUDIO=(-i tmp/musique.wav); else AUDIO=(-f lavfi -t "${DUREE}" -i anullsrc=r=44100:cl=stereo); fi
ffmpeg -y -loglevel error -framerate 30 -i tmp/frames/f%05d.jpg "${AUDIO[@]}" -map 0:v -map 1:a -t "${DUREE}" \
  -c:v libx264 -preset medium -crf 20 -profile:v high -pix_fmt yuv420p -r 30 -c:a aac -b:a 128k -movflags +faststart "videos/E-${JOB_ID}.mp4"
cp tmp/frames/f00080.jpg "videos/E-${JOB_ID}.jpg"
ls -la videos/
