# Persian narration quality audit — ImamAli110

## Scope and verified repository behavior

This audit is based on `app/spiritual_tts.py`, `app/emotion_tagger.py`, `config/channel.yaml`, and `requirements.txt` on `feat/openclaw-autonomous-manager-v2`.

- The channel requires a consistent male Persian narrator (`fa-IR`, currently `fa-IR-FaridNeural`).
- `synthesize_with_captions` segments narration by scene, inserts controlled pauses, and builds phrase captions from Edge TTS word-boundary metadata.
- The default workflow sets `TTS_PROVIDER=piper`, but the current provider selector deliberately switches away from the configured Piper path unless `ALLOW_FEMALE_TTS=1`, because the bundled Mana/Piper voice is female. The effective default is therefore Edge TTS with the male Farid neural voice.
- Edge TTS currently changes rate and pitch slightly based on heuristic emotion labels. The code itself correctly notes that Edge TTS has no native emotion styles; these are delivery hints, not expressive acting.
- ElevenLabs is supported as an optional provider with emotion tags and alignment, but it requires credentials and should not be the free default.

## Candidate audit

| Candidate | Persian suitability | Naturalness / expression | Cost and licensing notes | Decision |
|---|---|---|---|---|
| Microsoft Edge neural voice `fa-IR-FaridNeural` | Persian male voice; already integrated | Clear neural speech, but limited controllable emotional acting; rate/pitch are not true emotion controls | No API key in this repository; it is an online service, not an open-source model, and availability/terms can change | Keep as reliable no-key baseline and fallback |
| F5-TTS Persian fork (`sepehreghdami/F5-TTS-Persian`) | Promising Persian experimentation, but the repository README largely remains upstream F5-TTS documentation; a verified Persian production checkpoint and its usage terms must be confirmed before selecting it | Reference-audio conditioning can support expressive voice matching, but actual Persian quality must be auditioned with our script | Upstream code is MIT, but upstream pretrained models are marked CC-BY-NC. That is a blocker for monetized use unless the exact Persian checkpoint has separate commercial permission | GPU/Colab benchmark only after checkpoint and license verification; do not make it the production default yet |
| Coqui XTTS-v2 | Official supported-language list does not include Persian | Good voice cloning for its supported languages | Coqui Public Model License; Persian is not officially supported by XTTS-v2 | Do not select as the Persian backend |
| Persian-TTS-Zoo / older Persian Tacotron-family models | Persian-specific model collection exists | Quality, latency, checkpoints and current dependencies vary; no evidence yet that these beat the existing male neural baseline for this channel | Each linked model has its own license; repository is a catalog, not one unified inference package | Research candidate only; benchmark before integration |
| Kokoro 82M | Persian is not an officially established supported language in the core project | Lightweight, but that alone does not establish Persian pronunciation quality | Check exact model license and supported languages | Do not use for Persian without a verified Persian model |
| ElevenLabs v4 | Persian endpoint is already represented in the current integration | Supports emotion tags in this code path; likely a useful quality comparison | Paid/limited service, not a zero-cost default | Optional comparison only; never required for the free pipeline |

## Recommendation

1. **Preserve the current male Farid neural voice as the dependable no-key baseline.** Do not silently switch the channel to a female Piper voice.
2. **Improve delivery without pretending the voice has native emotion controls:** use natural Persian punctuation, phrase-level segmentation, restrained pauses, consistent loudness, and modest scene-specific pacing. Avoid aggressive pitch shifts that make the narrator sound synthetic.
3. **Benchmark F5-TTS Persian only on a GPU session** using the exact same 20–30 second Persian script and a clean, consented male reference recording. Compare pronunciation, stress, breathiness, emotional restraint, artifacts, speed, and voice consistency—not just a demo clip.
4. **Do not use XTTS-v2 as Persian-ready** based on its official language list. Do not deploy the F5 checkpoint for monetized channel content until its exact model license is verified; upstream F5 pretrained weights are marked non-commercial.
5. **Do not add a new TTS backend to the scheduled CPU workflow until caption timing is solved and tested.** The current captions depend on provider word-boundary/alignment metadata. An audio file that sounds better but causes guessed caption timings would regress the finished video.
6. **Do not fork `255kb/stack-on-a-budget` as a runtime dependency.** It is a curated directory of free-tier services, not a TTS engine or API. Use it as a discovery reference only; select a specific provider/model and verify its current limits and terms.

## Acceptance test before replacing the current voice

- Same Persian script, same male voice identity and same final audio loudness for every candidate.
- Native Persian pronunciation and punctuation pauses; no dropped/repeated words.
- Calm, warm, reflective delivery suitable for spiritual/motivational narration; energetic only on the opening hook.
- Captions aligned to actual speech, with no more than a small timing error at phrase boundaries.
- No model/service requiring payment or an undocumented API key in the zero-cost path.
- Save candidate audio privately for human review; do not upload a test voice or publish it automatically.
