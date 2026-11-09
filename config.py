import os
from pathlib import Path

# Base Paths (Cross-Platform Compatible)
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
SAVED_DIR = DATA_DIR / "edited_pdfs"
DB_PATH = DATA_DIR / "pdf_editor.db"

# Ensure all runtime directories exist
for directory in [DATA_DIR, UPLOADS_DIR, SAVED_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
