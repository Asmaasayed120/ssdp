import subprocess
import sys

# Use the SAME python that's running this script (venv python)
PYTHON = sys.executable

steps = [
    ("Generating prompts",   [PYTHON, "generate_prompts.py"]),
    ("Synthesizing audio",   [PYTHON, "synthesize.py"]),
    ("Exporting dataset",    [PYTHON, "export.py"]),
]

for name, cmd in steps:
    print(f"\n{'='*50}\n▶ {name}\n{'='*50}")
    result = subprocess.run(cmd, check=True)

print("\n✅ Pipeline complete — run review_app.py to review samples")