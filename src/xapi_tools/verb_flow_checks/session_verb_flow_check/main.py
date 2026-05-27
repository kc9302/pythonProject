# session_verb_flow_check/main.py
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from session_verb_flow_check.cli import main as cli_main

def build_default_args():
    return [
        "main.py",
        "--host", os.getenv("SVFC_HOST", "192.168.0.200"),
        "--port", os.getenv("SVFC_PORT", "27017"),
        "--username", os.getenv("SVFC_USER", "wickedstorm"),
        "--password", os.getenv("SVFC_PASS", "ws02020!!"),
        "--db", os.getenv("SVFC_DB", "lrs"),
        "--coll", os.getenv("SVFC_COLL", "statements"),
        "--start", os.getenv("SVFC_START", "2024-01"),
        "--end", os.getenv("SVFC_END", "2025-09"),
        "--profile-id", os.getenv("SVFC_PROFILE", "http://lecognizer.com/xapi/profiles/session"),
        "--fetch-mode", "month",
        "--log-keys-mode", "top", "--log-keys-top-k", "20",
        "--format", "ndjson",
        "--out-dir", "out", "--csv-include-keys",
        "--verbs", "all",  # ✅ 기본: logged-in + logged-out 둘 다
    ]

if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.argv = build_default_args()
    cli_main()
