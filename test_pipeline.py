import json
import pytest
from pathlib import Path
from generate_prompts import generate_prompts, normalize_egyptian, has_edge_case

# ── Test 1: Prompt generation count ──────────────────────────────────
def test_prompt_count():
    prompts = generate_prompts(100)
    assert len(prompts) == 100, f"Expected 100, got {len(prompts)}"

# ── Test 2: All prompts have required fields ──────────────────────────
def test_prompt_fields():
    prompts = generate_prompts(10)
    required = {"id", "text", "category", "char_count", "word_count", "edge_case_flags"}
    for p in prompts:
        assert required.issubset(p.keys()), f"Missing fields in {p}"

# ── Test 3: Normalize Egyptian Arabic ────────────────────────────────
def test_normalize():
    assert normalize_egyptian("ازيك") == "إزيك"
    assert normalize_egyptian("دلوقتى") == "دلوقتي"
    assert normalize_egyptian("إمبارح") == "امبارح"

# ── Test 4: Edge case detection ───────────────────────────────────────
def test_edge_case_detection():
    # Code switching
    flags = has_edge_case("الـ meeting اتأجل")
    assert "code_switching" in flags

    # Numbers
    flags = has_edge_case("عندي ٣ كتب")
    assert "contains_numbers" in flags

    # Clean text — no flags
    flags = has_edge_case("إزيك عامل إيه")
    assert flags == []

# ── Test 5: Export CSV exists and has data ────────────────────────────
def test_export_exists():
    csv_path = Path("data/output/metadata.csv")
    assert csv_path.exists(), "metadata.csv not found"

    import pandas as pd
    df = pd.read_csv(csv_path)
    assert len(df) > 0, "CSV is empty"
    assert "text" in df.columns
    assert "file_name" in df.columns

# ── Test 6: Audio files exist ─────────────────────────────────────────
def test_audio_files_exist():
    csv_path = Path("data/output/metadata.csv")
    import pandas as pd
    df = pd.read_csv(csv_path)

    missing = []
    for _, row in df.iterrows():
        audio = Path("data/output") / row["file_name"]
        if not audio.exists():
            missing.append(row["file_name"])

    assert len(missing) == 0, f"Missing audio files: {missing[:5]}"