# BAMO Persian Pocket TTS (ONNX / CPU) — isolated integration

This branch adds an **opt-in** Pocket TTS Persian engine. It does not change the
production default voice provider. The current Edge TTS / ElevenLabs fallback
chain remains available.

## Important license restriction

The weights in `Nimaone/pocket-tts-farsi-v2-onnx` inherit **CC-BY-NC-4.0**.
This is non-commercial: do not use this model or its generated audio in
monetized YouTube content, sponsorships, advertising, or other commercial
work unless the model author grants a separate license. The code intentionally
does not set this engine as the default.

## Enable for a local/non-commercial test

Install the optional dependencies:

```bash
python -m pip install -r requirements-tts-pocket.txt
```

Set environment variables:

```bash
TTS_PROVIDER=pocket-tts-onnx
POCKET_TTS_PACE=1.0
# Optional: provide a reference WAV (ideally 1–5 seconds)
POCKET_TTS_REFERENCE_VOICE=voices/my_reference.wav
```

If no reference voice is provided, the adapter uses the upstream repository's
`voices/male_hello.wav` sample. On first use it clones the ParSiGo runtime,
downloads the ONNX model package and the Persian phoneme tokenizer into
`.cache/persian_tts`. The model is cached there for subsequent runs.
Runtime inference is forced to `CPUExecutionProvider`; PyTorch and a GPU are
not used.

## Caption timing

The upstream ONNX engine returns audio, not forced word alignment. For
Pocket TTS, this integration estimates word timing from Persian word length
and generated audio duration. It is marked as **estimated** in the metadata;
it is not equivalent to Edge TTS word-boundary events or ElevenLabs alignment.
Review subtitles against the audio before publishing.

## CPU smoke test

GitHub Actions workflow:
`.github/workflows/bamo_pocket_tts_cpu.yml`

It generates a Persian WAV on an Ubuntu CPU runner and uploads the WAV plus a
JSON report as a seven-day artifact. It does not upload anything to YouTube.
