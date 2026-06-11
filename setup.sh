#!/bin/bash
# One-time setup: venv, deps, model download, resume embeddings.
set -e
cd "$(dirname "$0")"

if [ ! -d venv ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt

if [ ! -f .env ]; then
    cp .env.example .env
    echo ">> Created .env — fill in your API keys."
fi

echo ">> Drop your 6 resume PDFs into data/ (see config.py for names), then:"
python - <<'EOF'
from services import embeddings
import db
db.init()
print("Embedding resumes (first run downloads the model, ~90MB)...")
vecs = embeddings.precompute_resumes()
print(f"Done: {len(vecs)} resume variants embedded.")
EOF

echo ">> Setup complete. Test a cycle with: venv/bin/python main.py"
echo ">> Then add to cron:  0 */6 * * * cd $(pwd) && venv/bin/python main.py >> cron.log 2>&1"
