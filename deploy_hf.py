"""Deploy AutoJobFinder to a private Hugging Face Space.

Prereq: hf auth login   (or HF_TOKEN env var)
Usage:  venv/bin/python deploy_hf.py
"""
from huggingface_hub import HfApi

SPACE_README = """---
title: AutoJobFinder
emoji: "🎯"
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---
Private job-matching dashboard. Fetches jobs every 6h, scores them against
my resume variants with local embeddings, tracks applications.
"""

api = HfApi()
user = api.whoami()["name"]
repo_id = f"{user}/AutoJobFinder"

api.create_repo(repo_id, repo_type="space", space_sdk="docker",
                private=True, exist_ok=True)

api.upload_folder(
    folder_path=".",
    repo_id=repo_id,
    repo_type="space",
    ignore_patterns=["venv/*", ".git/*", ".gitignore", "embeddings/*",
                     "jobs.db", "*.log", ".env", ".claude/*", "README.md",
                     "__pycache__/*", "*/__pycache__/*", "setup.sh",
                     "deploy_hf.py"],
)
# Resume PDFs are gitignored locally; upload explicitly (Space is private).
# Must come after the folder upload so no .gitignore blocks them server-side.
api.upload_folder(folder_path="data", path_in_repo="data",
                  repo_id=repo_id, repo_type="space")
api.upload_file(path_or_fileobj=SPACE_README.encode(), path_in_repo="README.md",
                repo_id=repo_id, repo_type="space")

print(f"Deployed: https://huggingface.co/spaces/{repo_id}")
print("First build takes ~5 min. Set secrets (JSEARCH_API_KEY etc.) in"
      " Space settings -> Variables and secrets.")
