import asyncio
import json
import logging
import time
from pathlib import Path
import yaml
import edge_tts
import aiofiles
from pydub import AudioSegment

# ── Load config ──────────────────────────────────────────────────────
with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

PROMPTS_FILE   = Path(config["prompts"]["output_file"])
AUDIO_DIR      = Path(config["tts"]["audio_dir"] if "audio_dir" in config["tts"] else config["pipeline"]["audio_dir"])
CHECKPOINT     = Path(config["pipeline"]["checkpoint_file"])
LOG_FILE       = Path(config["pipeline"]["log_file"])
VOICE          = config["tts"]["voice"]
RATE           = config["tts"]["rate"]
VOLUME         = config["tts"]["volume"]
BATCH_SIZE     = config["tts"]["batch_size"]
RETRY_ATTEMPTS = config["tts"]["retry_attempts"]
RETRY_DELAY    = config["tts"]["retry_delay"]

AUDIO_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

# ── Logging ───────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)

# ── Checkpoint helpers ────────────────────────────────────────────────
def load_checkpoint() -> set:
    """Return set of already-synthesized prompt IDs."""
    if CHECKPOINT.exists():
        with open(CHECKPOINT, "r", encoding="utf-8") as f:
            data = json.load(f)
        done = set(data.get("completed", []))
        log.info(f"Checkpoint loaded — {len(done)} prompts already done")
        return done
    return set()

def save_checkpoint(completed: set):
    with open(CHECKPOINT, "w", encoding="utf-8") as f:
        json.dump({"completed": list(completed), "timestamp": time.time()}, f)

# ── Core synthesis ────────────────────────────────────────────────────
async def synthesize_one(prompt: dict, completed: set) -> dict:
    """Synthesize a single prompt with retry logic."""
    pid   = prompt["id"]
    text  = prompt["text"]
    out   = AUDIO_DIR / f"{pid}.wav"

    # Already done — skip
    if pid in completed:
        log.info(f"[SKIP] {pid} already synthesized")
        return {**prompt, "audio_path": str(out), "status": "skipped"}

    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            communicate = edge_tts.Communicate(text, VOICE, rate=RATE, volume=VOLUME)
            # Write to temp mp3 first, edge-tts default is mp3
            tmp = AUDIO_DIR / f"{pid}.mp3"
            await communicate.save(str(tmp))

            # Convert proper MP3 → WAV
            audio = AudioSegment.from_mp3(str(tmp))
            audio = audio.set_frame_rate(16000).set_channels(1)
            audio.export(str(out), format="wav")
            tmp.unlink()  # delete mp3
            log.info(f"[OK] {pid} → {out.name}")
            completed.add(pid)
            return {**prompt, "audio_path": str(out), "status": "success"}

        except Exception as e:
            log.warning(f"[RETRY {attempt}/{RETRY_ATTEMPTS}] {pid} — {e}")
            await asyncio.sleep(RETRY_DELAY * attempt)

    log.error(f"[FAIL] {pid} failed after {RETRY_ATTEMPTS} attempts")
    return {**prompt, "audio_path": None, "status": "failed"}

# ── Batch runner ──────────────────────────────────────────────────────
async def synthesize_all():
    # Load prompts
    with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
        prompts = json.load(f)

    completed = load_checkpoint()
    remaining = [p for p in prompts if p["id"] not in completed]
    log.info(f"Total: {len(prompts)} | Done: {len(completed)} | Remaining: {len(remaining)}")

    results = []

    # Add already-completed to results
    done_map = {p["id"]: p for p in prompts if p["id"] in completed}
    for pid, p in done_map.items():
        results.append({**p, "audio_path": str(AUDIO_DIR / f"{pid}.wav"), "status": "skipped"})

    # Process remaining in batches
    for i in range(0, len(remaining), BATCH_SIZE):
        batch = remaining[i : i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (len(remaining) + BATCH_SIZE - 1) // BATCH_SIZE
        log.info(f"── Batch {batch_num}/{total_batches} ({len(batch)} prompts) ──")

        tasks = [synthesize_one(p, completed) for p in batch]
        batch_results = await asyncio.gather(*tasks)
        results.extend(batch_results)

        # Save checkpoint after every batch
        save_checkpoint(completed)
        log.info(f"Checkpoint saved — {len(completed)} total completed")

        # Small pause between batches to avoid rate limiting
        if i + BATCH_SIZE < len(remaining):
            await asyncio.sleep(1)

    # Save manifest
    manifest_path = Path(config["pipeline"]["audio_dir"] if "audio_dir" in config["pipeline"] else "data/audio") / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    # Summary
    success = sum(1 for r in results if r["status"] in ("success", "skipped"))
    failed  = sum(1 for r in results if r["status"] == "failed")
    log.info(f"\n{'='*50}")
    log.info(f"✅ Synthesis complete")
    log.info(f"   Success: {success} | Failed: {failed}")
    log.info(f"   Manifest: {manifest_path}")
    log.info(f"{'='*50}")

    return results

# ── Entry point ───────────────────────────────────────────────────────
if __name__ == "__main__":
    asyncio.run(synthesize_all())