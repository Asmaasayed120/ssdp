# Synthetic Speech Data Pipeline (S.S.D.P.)

A production-ready pipeline for generating, synthesizing, reviewing, and exporting
Egyptian Arabic speech data for STT model fine-tuning.

---

## Pipeline Architecture
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  1. Prompt Gen  │───▶│  2. TTS Synth   │───▶│   3. Review     │───▶│   4. Export     │
│                 │    │                 │    │                 │    │                 │
│ generate_       │    │ synthesize.py   │    │ review_app.py   │    │ export.py       │
│ prompts.py      │    │ async + batch   │    │ Gradio UI       │    │ CSV + WAV       │
│                 │    │ + checkpoint    │    │ + auto QA       │    │ Whisper-ready   │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘

---

## Quickstart

```bash
# 1. Install dependencies
pip install edge-tts gradio pandas pydub aiofiles pyyaml pytest

# 2. Generate prompts
python generate_prompts.py

# 3. Synthesize audio
python synthesize.py

# 4. Review samples
python review_app.py
# Open http://127.0.0.1:7860 in your browser

# 5. Export dataset
python export.py
```

---

## Stage 1 — Prompt Generation

### Approach
Prompts were generated from a hand-curated bank of Egyptian Arabic sentences
organized into 7 categories:

| Category | Count | Purpose |
|---|---|---|
| `daily_conversation` | 15 | Common greetings and exchanges |
| `numbers_and_dates` | 15 | Numeric and temporal expressions |
| `places_and_directions` | 14 | Navigation and location |
| `food_and_orders` | 14 | Food ordering and restaurants |
| `questions_and_requests` | 14 | Requests and inquiries |
| `code_switching` | 14 | Arabic + English mixed speech |
| `edge_cases` | 14 | Hesitations, repetitions, exclamations |

### Rationale
- **Diversity by design:** Categories reflect real-world Egyptian Arabic usage domains
- **Edge case coverage:** Hesitations (`مممم`)، repeated words، and exclamations stress-test TTS
- **Code-switching:** Egyptian speakers routinely mix Arabic and English — ignoring this produces a dataset that fails on real speech
- **Normalization:** Common spelling variants (`ازيك` → `إزيك`) are canonicalized before synthesis

---

## Stage 2 — TTS Synthesis

### Model Choice: Microsoft Edge TTS (`ar-EG-ShakirNeural`)

| Option | Verdict |
|---|---|
| Edge TTS `ar-EG-ShakirNeural` | ✅ Chosen — Egyptian Arabic native voice, free, reliable |
| gTTS (Google) | ❌ MSA only, no Egyptian dialect support |
| Coqui TTS | ❌ No Arabic model with Egyptian dialect |
| Chatterbox (Resemble AI) | ❌ English-only, no Arabic support |
| ElevenLabs | ✅ Higher quality but requires paid API |

### Engineering Decisions
- **Async batching:** All synthesis runs concurrently in configurable batch sizes (default: 10)
- **Checkpointing:** Completed prompt IDs are saved after every batch — pipeline is fully resumable
- **Retry logic:** Each prompt retries up to 3 times with exponential backoff on failure
- **Output format:** WAV 16000Hz mono — matches Whisper fine-tuning requirements exactly
- **Manifest:** Every synthesized sample is logged to `data/audio/manifest.json`

### Known Limitations
Egyptian Arabic presents genuine challenges for off-the-shelf TTS:

1. **Dialect vocabulary** — Words like `دلوقتي`، `ازيك`، `تمام` have no MSA equivalent; the model pronounces them with a formal accent
2. **Code-switching** — The `ال` prefix on English words (`الـ meeting`) causes mispronunciation
3. **Colloquial phonemes** — Egyptian `ج` is pronounced /g/ not /dʒ/; Edge TTS uses the MSA pronunciation
4. **Hesitation tokens** — `مممم`، `يعني...` are not handled naturally by any current Arabic TTS
5. **Number reading** — Mixed Arabic-English numerals (`١٥ مارس`) are read inconsistently

These limitations are **by design observable** — the review stage exists precisely to catch and filter them.

---

## Stage 3 — Review

### Interface
A lightweight Gradio web app (`review_app.py`) for human-in-the-loop review.
Each sample displays the Egyptian Arabic text and synthesized audio side by side.
Reviewers can Accept, Reject, or navigate to the previous sample.
Decisions are saved automatically to `data/reviewed/reviewed.json`.

### Automated Quality Signals
Each sample is scored automatically before human review:

| Signal | Method | Threshold |
|---|---|---|
| **Duration** | WAV frame count / sample rate | 0.5s – 30s |
| **SNR estimate** | Signal vs. quietest 10% of frames | ≥ 10 dB |
| **Composite score** | 0.4 × duration_ok + 0.6 × SNR_normalized | ≥ 0.6 |

Samples below threshold are flagged `⚠️ low quality` before human review,
allowing reviewers to prioritize borderline cases.

### Review Output
All decisions are saved to `data/reviewed/reviewed.json` and survive app restarts.

---

## Stage 4 — Export Format

### Format: CSV + WAV

data/output/
├── audio/
│   ├── prompt_0001.wav
│   ├── prompt_0002.wav
│   └── ...
├── metadata.csv
└── dataset_info.json

### metadata.csv columns

| Column | Description |
|---|---|
| `id` | Unique prompt identifier |
| `file_name` | Relative path to WAV file |
| `text` | Egyptian Arabic transcript |
| `category` | Prompt category |
| `duration_sec` | Audio duration in seconds |
| `snr_db` | Estimated signal-to-noise ratio |
| `quality_score` | Composite quality score (0–1) |
| `edge_case_flags` | Pipe-separated list of flags |
| `review_status` | accepted / rejected / flagged / pending |

### Why CSV + WAV?
This format is directly compatible with Whisper fine-tuning via HuggingFace `datasets`:

```python
from datasets import Dataset, Audio
import pandas as pd

df = pd.read_csv("data/output/metadata.csv")
dataset = Dataset.from_pandas(df).cast_column("file_name", Audio())
```

---

## Observed Quality Issues

| Issue | Frequency | Mitigation |
|---|---|---|
| Formal accent on dialect words | High | Flag in review; document in dataset_info |
| Mispronounced code-switched terms | Medium | Review + reject worst cases |
| Inconsistent number reading | Medium | Edge case flag auto-applied |
| Unnatural hesitation tokens | Low | Flagged as edge_cases category |

---

## Trade-offs and Limitations

- **TTS ceiling:** No free Egyptian Arabic TTS produces native-quality dialect speech. Edge TTS is the best available free option but has a clear MSA bias.
- **Scale vs. quality:** At 100 samples this is a demonstration pipeline. Production scale would require 10,000+ samples and a paid TTS or a fine-tuned Arabic TTS model.
- **Synthetic data risk:** Models fine-tuned purely on synthetic data risk learning TTS artifacts (unnatural prosody, consistent mispronunciations) rather than real speech patterns. This pipeline mitigates that via the review stage but does not eliminate it.
- **Dialect coverage:** Egyptian Arabic has significant regional variation (Cairo vs. Upper Egypt vs. Alexandria). This corpus covers primarily Cairo dialect.

---

## Configuration

All parameters are externalized in `config.yaml`:

```yaml
tts:
  voice: "ar-EG-ShakirNeural"   # Change to switch TTS voice
  batch_size: 10                 # Tune for your connection speed
  retry_attempts: 3

quality:
  min_duration_sec: 0.5
  min_snr_db: 10.0
  min_quality_score: 0.6
```

---

## Project Structure
ssdp/
├── config.yaml
├── generate_prompts.py
├── synthesize.py
├── review_app.py
├── export.py
├── README.md
└── data/
├── prompts/prompts.json
├── audio/          ← synthesized WAVs + manifest.json
├── reviewed/       ← reviewed.json
├── output/         ← final dataset (CSV + WAV)
│   ├── audio/
│   ├── metadata.csv
│   └── dataset_info.json
├── checkpoint.json
└── pipeline.log
