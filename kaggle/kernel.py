# Kaggle Notebook script: GPU-generated ImamAli110 video
# This kernel intentionally fails instead of falling back to the old CPU cartoon renderer.
import os, sys, subprocess
from pathlib import Path

def run(cmd, **kwargs):
    print("+", " ".join(map(str, cmd)), flush=True)
    subprocess.run(cmd, check=True, **kwargs)

print("ImamAli110 GPU job starting", flush=True)
run(["nvidia-smi"])
run(["bash", "-lc", "git clone --depth 1 https://github.com/farzin0369/Youtube1.git /kaggle/working/Youtube1"])
os.chdir("/kaggle/working/Youtube1")

# Kaggle's base image may ship incompatible torch/torchao combinations. Keep its CUDA torch,
# remove only orphaned torchao, and install the model stack without replacing torch.
run([sys.executable, "-m", "pip", "install", "-q", "diffusers>=0.32,<0.42", "transformers>=4.46", "accelerate>=1.0", "safetensors", "imageio-ffmpeg", "piper-tts", "google-api-python-client", "google-auth-oauthlib", "google-auth-httplib2", "moviepy<2", "Pillow", "PyYAML", "requests", "openai", "numpy"])
run([sys.executable, "-m", "pip", "uninstall", "-y", "torchao"])

import torch
print("torch:", torch.__version__, "CUDA:", torch.cuda.is_available(), flush=True)
if not torch.cuda.is_available():
    raise RuntimeError("Kaggle did not attach a CUDA GPU. Enable Accelerator: GPU (T4 x2) in notebook settings.")

# Pull credentials from Kaggle Notebook Secrets; never store secrets in Git.
from kaggle_secrets import UserSecretsClient
secrets = UserSecretsClient()
def secret(name, required=False):
    try:
        value = secrets.get_secret(name)
        if value:
            os.environ[name] = value
            return value
    except Exception:
        pass
    if required:
        raise RuntimeError("Missing Kaggle Notebook Secret: " + name)
    return ""

secret("YOUTUBE_CLIENT_ID", True)
secret("YOUTUBE_CLIENT_SECRET", True)
secret("YOUTUBE_REFRESH_TOKEN", True)
secret("QWEN_API_KEY", False)
secret("DASHSCOPE_API_KEY", False)
os.environ.setdefault("AI_ENGINE", "qwen")
os.environ.setdefault("QWEN_MODEL", "qwen-plus")
os.environ.setdefault("QWEN_API_BASE", "https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
os.environ["VIDEO_ENGINE"] = "cogvideox"
os.environ["LOCAL_VIDEO_MODEL"] = "THUDM/CogVideoX-2b"
os.environ["VIDEO_CLIPS_SHORT"] = os.environ.get("VIDEO_CLIPS_SHORT", "4")
os.environ["VIDEO_FRAMES"] = os.environ.get("VIDEO_FRAMES", "49")
os.environ["VIDEO_STEPS"] = os.environ.get("VIDEO_STEPS", "25")
os.environ["VIDEO_GUIDANCE"] = os.environ.get("VIDEO_GUIDANCE", "6")
os.environ["TTS_PROVIDER"] = "piper"
os.environ["PIPER_MODEL"] = "/kaggle/working/fa_IR-amir-medium.onnx"
os.environ["HF_HOME"] = "/kaggle/working/hf-cache"

run(["bash", "-lc", "curl -L --fail --retry 3 -o /kaggle/working/fa_IR-amir-medium.onnx https://huggingface.co/rhasspy/piper-voices/resolve/main/fa/fa_IR/amir/medium/fa_IR-amir-medium.onnx && curl -L --fail --retry 3 -o /kaggle/working/fa_IR-amir-medium.onnx.json https://huggingface.co/rhasspy/piper-voices/resolve/main/fa/fa_IR/amir/medium/fa_IR-amir-medium.onnx.json"])
# First run is a PRIVATE YouTube upload for safety; public publishing is not enabled automatically.
run([sys.executable, "-m", "app.pipeline", "--kind", os.environ.get("VIDEO_KIND", "short"), "--publish-mode", "private"])
print("ImamAli110 GPU job finished", flush=True)
