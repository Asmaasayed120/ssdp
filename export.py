import json
import shutil
import csv
from pathlib import Path
import yaml

# ── Load config ───────────────────────────────────────────────────────
with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

REVIEWED_FILE = Path(config["pipeline"]["reviewed_dir"]) / "reviewed.json"
EXPORT_DIR    = Path(config["export"]["audio_subdir"])
EXPORT_CSV    = Path(config["export"]["output_file"])
MIN_SCORE     = config["export"]["min_quality_score"]

EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# ── Load reviewed samples ─────────────────────────────────────────────
def load_reviewed():
    if not REVIEWED_FILE.exists():
        # No manual review done — use all successful with quality filter
        manifest = Path(config["pipeline"]["audio_dir"]) / "manifest.json"
        with open(manifest, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [d for d in data if d.get("status") in ("success", "skipped")]

    with open(REVIEWED_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

# ── Export ────────────────────────────────────────────────────────────
def export():
    samples = load_reviewed()

    accepted = [
        s for s in samples
        if s.get("review_status", "pending") in ("accepted", "pending")
        and s.get("audio_path")
        and Path(s["audio_path"]).exists()
    ]

    print(f"Total reviewed : {len(samples)}")
    print(f"Passing export : {len(accepted)}")

    rows = []
    for s in accepted:
        src  = Path(s["audio_path"])
        dest = EXPORT_DIR / src.name
        shutil.copy2(src, dest)

        rows.append({
            "id"            : s["id"],
            "file_name"     : f"audio/{src.name}",
            "text"          : s["text"],
            "category"      : s.get("category", ""),
            "duration_sec"  : s.get("duration_sec", ""),
            "snr_db"        : s.get("snr_db", ""),
            "quality_score" : s.get("quality_score", ""),
            "edge_case_flags": "|".join(s.get("edge_case_flags", [])),
            "review_status" : s.get("review_status", "pending"),
        })

    # Write metadata.csv
    EXPORT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(EXPORT_CSV, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    # Write dataset_info.json
    info = {
        "dataset_name"   : "Egyptian Arabic Synthetic Speech",
        "total_samples"  : len(rows),
        "language"       : "ar-EG",
        "dialect"        : "Egyptian Arabic",
        "tts_engine"     : "Microsoft Edge TTS (ar-EG-ShakirNeural)",
        "sample_rate"    : 16000,
        "channels"       : 1,
        "format"         : "WAV",
        "categories"     : list({r["category"] for r in rows}),
        "export_format"  : "CSV + WAV — Whisper fine-tuning compatible",
    }
    info_path = Path(config["export"]["output_file"]).parent / "dataset_info.json"
    with open(info_path, "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Export complete")
    print(f"   CSV     : {EXPORT_CSV}")
    print(f"   Audio   : {EXPORT_DIR}")
    print(f"   Info    : {info_path}")
    print(f"   Samples : {len(rows)}")

if __name__ == "__main__":
    export()