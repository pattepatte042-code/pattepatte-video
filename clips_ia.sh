#!/usr/bin/env bash
# Clips video IA (Wan 2.2) fabriques sur le GPU gratuit de Kaggle, puis publies dans la release "clips-ia".
set -euo pipefail
[[ "${JOB_ID}" =~ ^[A-Za-z0-9_-]{1,60}$ ]] || { echo "job_id invalide"; exit 1; }
[[ -n "${KAGGLE_USERNAME:-}" && -n "${KAGGLE_KEY:-}" ]] || { echo "secrets Kaggle absents"; exit 1; }
pip install -q -U kaggle
rm -rf k out; mkdir -p k out
python3 - <<'PY'
import json, os
p = json.loads(os.environ['PROMPTS'])
assert isinstance(p, list) and p, 'prompts vides'
p = [str(x).replace('\n', ' ')[:600] for x in p][:6]
r = json.loads(os.environ.get('REGLAGES') or '{}')
r = {k: v for k, v in r.items() if k in ('h', 'w', 'frames', 'steps', 'max_s', 'bf16') and isinstance(v, int)}
src = open('kaggle_clips.py', encoding='utf-8').read()
open('k/clips.py', 'w', encoding='utf-8').write('PROMPTS = %s\nREGLAGES = %s\n' % (json.dumps(p), json.dumps(r)) + src)
u = os.environ['KAGGLE_USERNAME']
json.dump({'id': u + '/pap-clips-ia', 'title': 'pap-clips-ia', 'code_file': 'clips.py', 'language': 'python',
           'kernel_type': 'script', 'is_private': True, 'enable_gpu': True, 'enable_internet': True,
           'dataset_sources': [], 'competition_sources': [], 'kernel_sources': []}, open('k/kernel-metadata.json', 'w'))
print('prompts :', len(p), 'reglages :', r)
PY
ID="${KAGGLE_USERNAME}/pap-clips-ia"
kaggle kernels push -p k --accelerator NvidiaTeslaT4 || kaggle kernels push -p k
sleep 90
ETAT=""
for i in $(seq 1 165); do
  ETAT=$(kaggle kernels status "$ID" 2>&1 || true)
  echo "$(date +%H:%M) $ETAT"
  case "${ETAT,,}" in *complete*|*error*|*cancel*) break;; esac
  sleep 60
done
kaggle kernels output "$ID" -p out || true
find out -type f | head -50
[ -f out/journal.json ] && cat out/journal.json || find out -name journal.json -exec cat {} \;
gh release view clips-ia >/dev/null 2>&1 || gh release create clips-ia --title "Clips IA Patte a Patte" --notes "Clips video IA (Wan 2.2, Apache 2.0) fabriques sur Kaggle."
mkdir -p envoi
J=$(find out -name journal.json | head -1); [ -n "$J" ] && cp "$J" "envoi/IA-${JOB_ID}-journal.json"
n=0
for f in $(find out -name 'c*.mp4' | sort); do
  cp "$f" "envoi/IA-${JOB_ID}-$(basename "$f")"; n=$((n+1))
done
for f in envoi/*; do gh release upload clips-ia "$f" --clobber; done
echo "clips publies : $n"
[ "$n" -gt 0 ] || { echo "aucun clip"; exit 1; }
