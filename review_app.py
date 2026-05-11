import json
import wave
import math
import struct
from pathlib import Path
import gradio as gr
import pandas as pd
import yaml

# ── Load config ───────────────────────────────────────────────────────
with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

MANIFEST   = Path(config["pipeline"]["audio_dir"]) / "manifest.json"
REVIEWED   = Path(config["pipeline"]["reviewed_dir"])
REVIEWED.mkdir(parents=True, exist_ok=True)
REVIEW_OUT = REVIEWED / "reviewed.json"

MIN_DUR = config["quality"]["min_duration_sec"]
MAX_DUR = config["quality"]["max_duration_sec"]
MIN_SNR = config["quality"]["min_snr_db"]

# ── Audio quality helpers ─────────────────────────────────────────────
def get_duration(path: str) -> float:
    try:
        with wave.open(path, "rb") as w:
            return w.getnframes() / w.getframerate()
    except:
        return 0.0

def get_snr(path: str) -> float:
    """Simple SNR estimate from WAV file."""
    try:
        with wave.open(path, "rb") as w:
            frames = w.readframes(w.getnframes())
            sampwidth = w.getsampwidth()

        fmt = {1: "b", 2: "h", 4: "i"}.get(sampwidth, "h")
        samples = list(struct.unpack(f"{len(frames)//sampwidth}{fmt}", frames))

        if not samples:
            return 0.0

        signal_power = sum(s**2 for s in samples) / len(samples)
        # Estimate noise from quietest 10% of frames
        sorted_sq = sorted(s**2 for s in samples)
        noise_samples = sorted_sq[:max(1, len(sorted_sq)//10)]
        noise_power = sum(noise_samples) / len(noise_samples)

        if noise_power == 0:
            return 99.0
        snr = 10 * math.log10(signal_power / noise_power)
        return round(snr, 2)
    except:
        return 0.0

def quality_score(duration: float, snr: float) -> float:
    """0.0 – 1.0 composite quality score."""
    dur_ok  = MIN_DUR <= duration <= MAX_DUR
    snr_ok  = snr >= MIN_SNR
    dur_score = 1.0 if dur_ok else 0.0
    snr_score = min(snr / 40.0, 1.0) if snr > 0 else 0.0
    return round((dur_score * 0.4) + (snr_score * 0.6), 3)

# ── Load & enrich manifest ────────────────────────────────────────────
def load_manifest():
    with open(MANIFEST, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Load existing reviews if any
    existing = {}
    if REVIEW_OUT.exists():
        with open(REVIEW_OUT, "r", encoding="utf-8") as f:
            for item in json.load(f):
                existing[item["id"]] = item.get("review_status", "pending")

    enriched = []
    for item in data:
        if item.get("status") != "success" and item.get("status") != "skipped":
            continue
        path = item.get("audio_path", "")
        dur  = get_duration(path) if path else 0.0
        snr  = get_snr(path) if path else 0.0
        qs   = quality_score(dur, snr)
        enriched.append({
            **item,
            "duration_sec"   : round(dur, 2),
            "snr_db"         : snr,
            "quality_score"  : qs,
            "auto_flag"      : "⚠️ low quality" if qs < config["export"]["min_quality_score"] else "✅ ok",
            "review_status"  : existing.get(item["id"], "pending"),
        })
    return enriched

samples = load_manifest()
reviewed_map = {s["id"]: s for s in samples}

# ── Save reviews ──────────────────────────────────────────────────────
def save_reviews():
    with open(REVIEW_OUT, "w", encoding="utf-8") as f:
        json.dump(list(reviewed_map.values()), f, ensure_ascii=False, indent=2)

# ── Gradio helpers ────────────────────────────────────────────────────
def get_pending():
    return [s for s in reviewed_map.values() if s["review_status"] == "pending"]

def get_stats():
    total    = len(reviewed_map)
    accepted = sum(1 for s in reviewed_map.values() if s["review_status"] == "accepted")
    rejected = sum(1 for s in reviewed_map.values() if s["review_status"] == "rejected")
    flagged  = sum(1 for s in reviewed_map.values() if s["review_status"] == "flagged")
    pending  = total - accepted - rejected - flagged
    return f"📊 Total: {total} | ✅ Accepted: {accepted} | ❌ Rejected: {rejected} | ⚠️ Flagged: {flagged} | ⏳ Pending: {pending}"

# State
state = {"idx": 0, "queue": [s["id"] for s in samples]}

def get_current():
    if not state["queue"]:
        return None
    idx = state["idx"] % len(state["queue"])
    pid = state["queue"][idx]
    return reviewed_map.get(pid)

def show_current():
    s = get_current()
    if not s:
        return "No samples", None
    return (
        s["text"],
        s.get("audio_path"),
    )

def review(action):
    s = get_current()
    if s:
        reviewed_map[s["id"]]["review_status"] = action
        save_reviews()
    state["idx"] = (state["idx"] + 1) % max(len(state["queue"]), 1)
    return show_current()

def prev_sample():
    state["idx"] = (state["idx"] - 1) % max(len(state["queue"]), 1)
    return show_current()

def filter_view(filt):
    state["queue"] = [
        s["id"] for s in samples
        if filt == "all" or s["review_status"] == filt
        or (filt == "auto_flagged" and s["auto_flag"] == "⚠️ low quality")
    ]
    state["idx"] = 0
    return show_current()

def export_table():
    rows = []
    for s in reviewed_map.values():
        rows.append({
            "ID": s["id"], "Text": s["text"], "Category": s["category"],
            "Duration": s["duration_sec"], "SNR": s["snr_db"],
            "Quality": s["quality_score"], "Auto Flag": s["auto_flag"],
            "Status": s["review_status"]
        })
    return pd.DataFrame(rows)

# ── Gradio UI ─────────────────────────────────────────────────────────
with gr.Blocks(title="SSDP Review Tool") as app:
    gr.Markdown("# 🎙️ SSDP — Egyptian Arabic Speech Review Tool")

    text_out  = gr.Textbox(label="Egyptian Arabic Text", interactive=False)
    audio_out = gr.Audio(label="Synthesized Audio", interactive=False)


    with gr.Row():
        btn_prev   = gr.Button("⬅️ Prev")
        btn_accept = gr.Button("✅ Next", variant="primary")
        btn_reject = gr.Button("❌ Reject", variant="stop")


    outputs = [text_out, audio_out]

    app.load(show_current, outputs=outputs)

    btn_prev.click(prev_sample, outputs=outputs)
    btn_accept.click(lambda: review("accepted"), outputs=outputs)
    btn_reject.click(lambda: review("rejected"), outputs=outputs)

if __name__ == "__main__":
    app.launch()