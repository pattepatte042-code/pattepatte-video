#!/usr/bin/env bash
# Carrousel educatif (1080x1350) : vraies photos en arriere-plan (une par image si fournie)
set -euo pipefail
[[ "${JOB_ID}" =~ ^[A-Za-z0-9_-]{1,60}$ ]] || { echo "job_id invalide"; exit 1; }
mkdir -p videos tmp polices
for p in Bold Medium Regular; do
  curl -fsSL --retry 4 -o "polices/Poppins-${p}.ttf" "https://github.com/google/fonts/raw/main/ofl/poppins/Poppins-${p}.ttf" || true
done
printf '%s' "${SPEC}" > tmp/spec.json
python3 -c "import json;json.load(open('tmp/spec.json'))" || { echo "spec JSON invalide"; exit 1; }
autorisee() {
  case "$1" in
    https://pattepatte.app.n8n.cloud/*|https://automations.gh-soft.net/*|https://pixabay.com/*|https://cdn.pixabay.com/*|https://upload.wikimedia.org/*|https://images.pexels.com/*) return 0;;
    *) return 1;;
  esac
}
telecharger() {
  autorisee "$1" || { echo "adresse refusee : $1"; return 1; }
  curl -fsSL --retry 5 --retry-delay 4 -A "Mozilla/5.0 (pattepatte)" -o "$2" "$1" && python3 -c "from PIL import Image;Image.open('$2').verify()"
}
PHOTO=""
if [[ -n "${IMAGE_URL:-}" ]]; then
  telecharger "${IMAGE_URL}" tmp/photo.jpg && PHOTO=tmp/photo.jpg || { rm -f tmp/photo.jpg; PHOTO=""; }
fi
# une vraie photo par image : slides[k].photo_url
python3 -c "
import json
s=json.load(open('tmp/spec.json')).get('slides',[])
for k,x in enumerate(s[:8],1):
    u=str(x.get('photo_url') or '').strip()
    if u: print(k, u)
" > tmp/photos.txt
while read -r k u; do
  telecharger "$u" "tmp/photo_${k}.jpg" || rm -f "tmp/photo_${k}.jpg"
done < tmp/photos.txt
echo "photos par image : $(ls tmp/photo_*.jpg 2>/dev/null | wc -l)"
PHOTOS_DIR=tmp POLICES_DIR=polices python3 carousel.py tmp/spec.json tmp "${JOB_ID}" ${PHOTO}
cp tmp/C-"${JOB_ID}"-*.jpg videos/
ls -la videos/
