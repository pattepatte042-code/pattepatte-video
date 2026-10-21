#!/usr/bin/env bash
# Fabrique un Reel 1080x1920 a partir de la carte Patte a Patte (1080x1350).
set -euo pipefail
[[ "${JOB_ID}" =~ ^[A-Za-z0-9_-]{1,60}$ ]] || { echo "job_id invalide"; exit 1; }
[[ "${IMAGE_URL}" == https://pattepatte.app.n8n.cloud/* ]] || { echo "adresse d image refusee"; exit 1; }
[[ "${DUREE:-12}" =~ ^[0-9]{1,2}$ ]] && DUREE="${DUREE:-12}" || DUREE=12
(( DUREE < 6 )) && DUREE=6
mkdir -p videos tmp
curl -fsSL --retry 5 --retry-delay 4 -o tmp/carte.jpg "${IMAGE_URL}"
# Musique originale generee (aucun droit d auteur tiers) ; silence si echec
if python3 music.py "${DUREE}" "${JOB_ID}" tmp/musique.wav; then AUDIO=(-i tmp/musique.wav); else AUDIO=(-f lavfi -t "${DUREE}" -i anullsrc=r=44100:cl=stereo); fi
FIN=$(awk "BEGIN{print ${DUREE}-0.7}")
ffmpeg -y -loglevel error \
  -loop 1 -framerate 30 -t "${DUREE}" -i tmp/carte.jpg \
  "${AUDIO[@]}" \
  -filter_complex "[0:v]split=2[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=40:4,eq=brightness=-0.12[bg];[b]scale=w='trunc(1000*(1+0.06*t/${DUREE})/2)*2':h=-2:eval=frame,crop=1000:1250[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2-40,fade=t=in:st=0:d=0.5,fade=t=out:st=${FIN}:d=0.7,format=yuv420p[v]" \
  -map "[v]" -map 1:a -c:v libx264 -preset medium -crf 21 -profile:v high -r 30 \
  -c:a aac -b:a 128k -shortest -movflags +faststart "videos/${JOB_ID}.mp4"
ls -la "videos/${JOB_ID}.mp4"
