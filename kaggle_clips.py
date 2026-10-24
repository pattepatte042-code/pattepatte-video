# Patte a Patte : clips video IA (Wan 2.2 TI2V-5B, licence Apache 2.0) fabriques sur le GPU gratuit de Kaggle.
# Les consignes (PROMPTS) sont ajoutees en tete de ce fichier par GitHub Actions avant l envoi.
import os, sys, json, time, subprocess, traceback
os.environ.setdefault('HF_HOME', '/tmp/hf')
DEBUT = time.time()
JOURNAL = {'etapes': [], 'clips': []}
OUT = '/kaggle/working/clips'
os.makedirs(OUT, exist_ok=True)

def note(msg):
    t = round(time.time() - DEBUT, 1)
    print('[%6.1fs] %s' % (t, msg), flush=True)
    JOURNAL['etapes'].append([t, msg])
    json.dump(JOURNAL, open('/kaggle/working/journal.json', 'w'), ensure_ascii=False, indent=1)

try:
    note('installation')
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q', '-U', 'diffusers>=0.35.0', 'transformers', 'accelerate', 'ftfy', 'imageio', 'imageio-ffmpeg'], check=True)
    import torch
    from diffusers import AutoencoderKLWan, WanPipeline
    from diffusers.utils import export_to_video
    note('gpu : %s' % (torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'AUCUN'))
    MID = 'Wan-AI/Wan2.2-TI2V-5B-Diffusers'
    dt = torch.bfloat16 if torch.cuda.is_available() and torch.cuda.is_bf16_supported() else torch.float16
    vae = AutoencoderKLWan.from_pretrained(MID, subfolder='vae', torch_dtype=torch.float32)
    pipe = WanPipeline.from_pretrained(MID, vae=vae, torch_dtype=dt)
    pipe.enable_model_cpu_offload()
    try:
        pipe.vae.enable_tiling()
    except Exception:
        pass
    note('modele charge (%s)' % dt)
    NEG = ('blurry, low quality, distorted, deformed animal, extra legs, extra heads, bad anatomy, text, watermark, logo, '
           'people, human, hands, static, frozen, cartoon, ugly')
    for k, p in enumerate(PROMPTS[:6]):
        t0 = time.time()
        try:
            img = pipe(prompt=p, negative_prompt=NEG, height=REGLAGES.get('h', 832), width=REGLAGES.get('w', 480),
                       num_frames=REGLAGES.get('frames', 73), num_inference_steps=REGLAGES.get('steps', 30),
                       guidance_scale=5.0, generator=torch.Generator('cpu').manual_seed(1000 + k)).frames[0]
            f = os.path.join(OUT, 'c%d.mp4' % k)
            export_to_video(img, f, fps=24)
            JOURNAL['clips'].append({'k': k, 'fichier': 'c%d.mp4' % k, 'secondes': round(time.time() - t0, 1), 'prompt': p})
            note('clip %d fait en %.0f s' % (k, time.time() - t0))
        except Exception as e:
            note('clip %d ERREUR : %s' % (k, str(e)[:300]))
            torch.cuda.empty_cache()
        if time.time() - DEBUT > REGLAGES.get('max_s', 7200):
            note('temps maximum atteint, arret')
            break
    note('termine')
except Exception as e:
    note('ERREUR GENERALE : ' + traceback.format_exc()[-1500:])
