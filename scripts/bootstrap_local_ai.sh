#!/usr/bin/env bash
set -euo pipefail
python3 -m venv .venv-local
source .venv-local/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-local.txt
echo "Local video engine ready."
echo "Install Ollama and a local model, install Piper with a Persian voice,"
echo "then run this on an NVIDIA CUDA machine."
