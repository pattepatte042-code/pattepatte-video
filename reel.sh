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
# vraies videos d animaux (Pixabay, libres de droits) : 1 clip par scene, recadre en vertical
mkdir -p tmp/clips; k=0; set -f
for U in ${VIDEO_URLS:-}; do
  case "$U" in https://cdn.pixabay.com/*) ;; *) echo "clip refuse"; continue;; esac
  [[ $k -ge 6 ]] && break
  if curl -fsSL --retry 4 --retry-delay 3 --max-time 90 -A "Mozilla/5.0 (pattepatte)" -o "tmp/clips/c$k.mp4" "$U"; then
    mkdir -p "tmp/clips/c$k"
    ffmpeg -y -loglevel error -ss 0.5 -i "tmp/clips/c$k.mp4" -t 4.5 -an \
      -filter_complex "[0:v]fps=30,split[a][b];[a]scale=540:960:force_original_aspect_ratio=increase,crop=540:960,boxblur=18:2,eq=brightness=-0.10:saturation=1.25,scale=1080:1920[bg];[b]scale=1080:780:force_original_aspect_ratio=increase:flags=lanczos,crop=1080:780,eq=contrast=1.05:saturation=1.10[fg];[bg][fg]overlay=0:1110" \
      -q:v 3 "tmp/clips/c$k/g%05d.jpg" || rm -rf "tmp/clips/c$k"
    rm -f "tmp/clips/c$k.mp4"; k=$((k+1))
  fi
done
set +f
echo "clips video : $k"
# voix off (Kokoro, Apache 2.0) : une phrase lue par diapo, la duree des diapos suit la voix
SPECF=tmp/spec.json
if [[ "${VOIX_OFF:-0}" == "1" ]]; then
  for f in kokoro-v1.0.onnx voices-v1.0.bin; do
    [ -f "$f" ] || curl -fsSL --retry 4 -o "$f" "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/$f" || true
  done
  if VOIX="${VOIX_NOM:-am_puck}" python3 voix_slides.py tmp/spec.json tmp/voix.wav tmp/spec_voix.json; then SPECF=tmp/spec_voix.json; else echo "voix off impossible, Reel sans voix"; fi
fi
CLIPS_DIR=tmp/clips POLICES_DIR=polices python3 reel.py "$SPECF" "${PHOTO:-aucune}" tmp/frames
DUREE=$(cat tmp/frames/duree.txt)
if python3 music.py "${DUREE}" "${JOB_ID}" tmp/musique.wav; then MUS=(-i tmp/musique.wav); else MUS=(-f lavfi -t "${DUREE}" -i anullsrc=r=44100:cl=stereo); fi
# post-production son : bruitages originaux + mixage + normalisation du volume (-14 LUFS, standard des reseaux)
if python3 sfx.py tmp/frames/coupes.txt "${DUREE}" tmp/sfx.wav; then SFX=(-i tmp/sfx.wav); else SFX=(-f lavfi -t "${DUREE}" -i anullsrc=r=44100:cl=stereo); fi
if [[ "$SPECF" == tmp/spec_voix.json ]]; then VO=(-i tmp/voix.wav); MIXF="[1:a]volume=0.22[m];[2:a]volume=0.5[s];[3:a]aresample=44100,pan=stereo|c0=c0|c1=c0,volume=1.0[v];[m][s][v]amix=inputs=3:duration=first:normalize=0"; else VO=(); MIXF="[1:a]volume=0.8[m];[2:a]volume=0.9[s];[m][s]amix=inputs=2:duration=first:normalize=0"; fi
ffmpeg -y -loglevel error -framerate 30 -i tmp/frames/f%05d.jpg "${MUS[@]}" "${SFX[@]}" "${VO[@]}" \
  -filter_complex "${MIXF},afade=t=out:st=$(python3 -c "print(max(0,${DUREE}-0.6))"):d=0.6,loudnorm=I=-14:TP=-1.5:LRA=11[a]" \
  -map 0:v -map "[a]" -t "${DUREE}" \
  -c:v libx264 -preset medium -crf 19 -profile:v high -pix_fmt yuv420p -r 30 -c:a aac -b:a 160k -ar 44100 -movflags +faststart "videos/E-${JOB_ID}.mp4"
cp tmp/frames/f00030.jpg "videos/E-${JOB_ID}.jpg"
ls -la videos/
