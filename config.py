"""Application settings loaded from environment variables."""
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
POLICY_DIR = Path(os.getenv("POLICY_DIR", ROOT_DIR / "data" / "sample_policies"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
TOP_K = int(os.getenv("POLICY_TOP_K", "5"))
