#!/usr/bin/env bash
set -euo pipefail

echo "=== install node/ffmpeg ==="
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt-get install -y -qq nodejs ffmpeg > /dev/null
node -v
ffmpeg -version | head -1

echo "=== clone composition ==="
rm -rf /content/Youtube1
git clone --depth 1 -b feat/bamo-openmontage-autonomous-studio https://github.com/farzin0369/Youtube1.git /content/Youtube1
cd /content/Youtube1/productions/bamo-time-dilation

echo "=== TTS ==="
pip install -q edge-tts
mkdir -p assets
python3 - <<'PY'
import asyncio, edge_tts
text = (
  "Time is not the same for everyone. "
  "Near a black hole, one second can equal years on Earth. "
  "GPS satellites already correct for this every day. "
  "Relativity is not theory on a chalkboard. It runs the modern world. "
  "BAMO. Follow at twelve bamo."
)
asyncio.run(edge_tts.Communicate(text, "en-US-GuyNeural").save("assets/narration.mp3"))
print("tts ok")
PY

echo "=== HyperFrames 0.9.19 render --gpu ==="
npx --yes hyperframes@0.9.19 render --gpu -o /content/BAMO_TimeDilation_HyperFrames_GPU_@12bamo.mp4 \
  || npx --yes hyperframes@0.9.19 render -o /content/BAMO_TimeDilation_HyperFrames_GPU_@12bamo.mp4

ls -lh /content/BAMO_TimeDilation_HyperFrames_GPU_@12bamo.mp4
ffprobe -v error -show_entries stream=width,height,codec_name -show_entries format=duration,size -of default=nw=1 /content/BAMO_TimeDilation_HyperFrames_GPU_@12bamo.mp4 || true
echo "=== DONE ==="
