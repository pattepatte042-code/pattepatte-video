#!/usr/bin/env bash
# Carrousel educatif : fond uni colore, gros chiffres, icones (1080x1350)
set -euo pipefail
[[ "${JOB_ID}" =~ ^[A-Za-z0-9_-]{1,60}$ ]] || { echo "job_id invalide"; exit 1; }
mkdir -p videos tmp polices
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
    *) echo "adresse d image refusee, couverture sans photo";;
  esac
fi
POLICES_DIR=polices python3 carousel.py tmp/spec.json tmp "${JOB_ID}" ${PHOTO}
cp tmp/C-"${JOB_ID}"-*.jpg videos/
ls -la videos/
