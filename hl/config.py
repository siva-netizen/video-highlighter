import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = PROJECT_ROOT / "skills"
DEFAULT_WORK_DIR = PROJECT_ROOT / "work"

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
STT_MODEL = os.environ.get("STT_MODEL", "whisper-large-v3-turbo")
SCORER_MODEL = os.environ.get("SCORER_MODEL", "openai/gpt-oss-120b")
ROUTER_MODEL = os.environ.get("ROUTER_MODEL", "openai/gpt-oss-20b")

WHISPER_CHUNK_SECONDS = 600
CONTENT_DETECTOR_THRESHOLD = 27.0
MIN_CLIP_SECONDS = 4.0
MAX_CLIP_SECONDS = 40.0
MIN_SHOT_SECONDS = 2.0
PHASH_HAMMING_MAX = 8
HIST_CORR_DUPLICATE_MIN = 0.95
CRITIC_MAX_LOOPS = 2


def require_groq_key() -> str:
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return GROQ_API_KEY
