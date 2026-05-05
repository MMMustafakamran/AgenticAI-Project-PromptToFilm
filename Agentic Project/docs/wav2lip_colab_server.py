# ============================================================
# Wav2Lip Lipsync API Server — Google Colab
# ------------------------------------------------------------
# Paste each CELL block into a separate Colab cell and run
# them in order.
#
# Exposes:  POST /lipsync
# Input:    { "image": "<base64 jpg/png>", "audio": "<base64 wav>" }
# Output:   { "status": "success", "data": "<base64 mp4>" }
#
# After running Cell 4, copy the printed LIPSYNC_API_URL value
# into your local .env file.
# ============================================================


# ==============================================================
# CELL 1 — Clone Wav2Lip & install dependencies
# ==============================================================
"""
!git clone https://github.com/Rudrabha/Wav2Lip /content/Wav2Lip
%cd /content/Wav2Lip

!pip install -q -r requirements.txt
!pip install -q librosa==0.9.1 torch==2.5.1 torchvision==0.20.1
!pip install -q fastapi uvicorn pyngrok nest_asyncio ffmpeg-python
!apt-get install -qq ffmpeg
"""


# ==============================================================
# CELL 2 — Download model weights
# ==============================================================
"""
import os
os.makedirs("/content/Wav2Lip/checkpoints", exist_ok=True)

# Wav2Lip GAN model from HuggingFace (~438 MB) — avoids Google Drive rate limits
!wget -q --show-progress \
     "https://huggingface.co/numz/wav2lip_studio/resolve/main/Wav2Lip/wav2lip_gan.pth" \
     -O /content/Wav2Lip/checkpoints/wav2lip_gan.pth

# Verify download succeeded (file should be ~438 MB)
import os
size_mb = os.path.getsize("/content/Wav2Lip/checkpoints/wav2lip_gan.pth") / 1e6
print(f"wav2lip_gan.pth: {size_mb:.1f} MB")
assert size_mb > 400, "Download looks incomplete — re-run this cell"

# Face detection backbone (s3fd)
!wget -q \
     "https://www.adrianbulat.com/downloads/python-fan/s3fd-619a316812.pth" \
     -O /content/Wav2Lip/face_detection/detection/sfd/s3fd.pth

print("✅ Models downloaded")
"""


# ==============================================================
# CELL 3 — Verify GPU is available
# ==============================================================
"""
import torch
print("GPU available:", torch.cuda.is_available())
print("Device:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU")
"""


# ==============================================================
# CELL 4 — Start the FastAPI + ngrok server
# ==============================================================
"""
import os
import base64
import subprocess
import tempfile
import threading
import uuid

import nest_asyncio
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from pyngrok import ngrok

nest_asyncio.apply()
os.chdir("/content/Wav2Lip")

app = FastAPI()

CHECKPOINT = "/content/Wav2Lip/checkpoints/wav2lip_gan.pth"

class LipsyncRequest(BaseModel):
    image: str   # base64-encoded JPG or PNG (character portrait)
    audio: str   # base64-encoded WAV
    type: str = "lipsync"


@app.get("/health")
def health():
    return {"status": "ok", "model": "wav2lip_gan"}


@app.post("/lipsync")
def lipsync(req: LipsyncRequest):
    tmp_dir = tempfile.mkdtemp()
    face_path   = os.path.join(tmp_dir, "face.png")
    audio_path  = os.path.join(tmp_dir, "audio.wav")
    output_path = os.path.join(tmp_dir, f"result_{uuid.uuid4().hex[:8]}.mp4")

    try:
        # 1. Decode inputs
        with open(face_path, "wb") as f:
            f.write(base64.b64decode(req.image))
        with open(audio_path, "wb") as f:
            f.write(base64.b64decode(req.audio))

        # 2. Run Wav2Lip inference
        cmd = [
            "python", "inference.py",
            "--checkpoint_path", CHECKPOINT,
            "--face",   face_path,
            "--audio",  audio_path,
            "--outfile", output_path,
            "--resize_factor", "1",  # keep original resolution
            "--nosmooth",            # skip temporal smoothing (faster)
            "--pads", "0", "10", "0", "0",  # slight vertical pad for chin
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

        if result.returncode != 0:
            print("Wav2Lip stderr:", result.stderr[-2000:])
            return {"status": "error", "message": result.stderr[-500:]}

        if not os.path.exists(output_path):
            return {"status": "error", "message": "Output file not created"}

        # 3. Return result as base64
        with open(output_path, "rb") as f:
            video_b64 = base64.b64encode(f.read()).decode()

        print(f"✅ Lipsync complete → {output_path}")
        return {"status": "success", "data": video_b64}

    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "Wav2Lip inference timed out (>300s)"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
    finally:
        # Clean up temp files
        for path in [face_path, audio_path, output_path]:
            try:
                os.remove(path)
            except FileNotFoundError:
                pass


# ── Start ngrok + uvicorn ──────────────────────────────────
ngrok.set_auth_token("")   # ← paste your ngrok auth token here

public_url = ngrok.connect(8001).public_url
print("=" * 55)
print("LIPSYNC_API_URL=" + public_url + "/lipsync")
print("=" * 55)
print("Add the above line to your local .env file")


def run_server():
    uvicorn.run(app, host="0.0.0.0", port=8001)

threading.Thread(target=run_server, daemon=True).start()
"""
