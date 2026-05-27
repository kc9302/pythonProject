# assessment_verb_flow_check/main.py
import os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from assessment_verb_flow_check.cli import main as cli_main

def build_default_args():
    return [
        "main.py",
        "--host", os.getenv("AVFC_HOST","192.168.0.200"),
        "--port", os.getenv("AVFC_PORT","27017"),
        "--username", os.getenv("AVFC_USER","wickedstorm"),
        "--password", os.getenv("AVFC_PASS","ws02020!!"),
        "--db", os.getenv("AVFC_DB","lrs"),
        "--coll", os.getenv("AVFC_COLL","statements"),
        "--start", os.getenv("AVFC_START","2024-01"),
        "--end", os.getenv("AVFC_END","2025-09"),
        "--profile-id", os.getenv("AVFC_PROFILE","http://lecognizer.com/xapi/profiles/assessment"),
        "--fetch-mode", "month",
        "--log-keys-mode", "top", "--log-keys-top-k", "20",
        "--format", "ndjson",
        "--out-dir", "out", "--csv-include-keys",
        "--verbs", "all",
    ]

if __name__ == "__main__":
    if len(sys.argv) == 1:
        sys.argv = build_default_args()
    cli_main()
