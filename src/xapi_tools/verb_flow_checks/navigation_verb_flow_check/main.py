# main.py
import os
import sys
from pathlib import Path

# 루트 경로 패키지 인식 보정
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from navigation_verb_flow_check.cli import main as cli_main


def build_default_args():
    """
    인자를 주지 않고 실행할 때 기본값을 채워 sys.argv를 구성한다.
    - 스트리밍 모드 고정
    - 달마다 쿼리(fetch-mode=month)
    - 로그 및 포맷 기본 지정
    """
    host = os.getenv("SVFC_HOST", "192.168.0.200")
    port = os.getenv("SVFC_PORT", "27017")
    user = os.getenv("SVFC_USER", "wickedstorm")
    pw = os.getenv("SVFC_PASS", "ws02020!!")
    db = os.getenv("SVFC_DB", "lrs")
    coll = os.getenv("SVFC_COLL", "statements")
    start = os.getenv("SVFC_START", "2024-01")
    end = os.getenv("SVFC_END", "2025-09")
    verb = os.getenv(
        "SVFC_VERB",
        "http://lecognizer.com/xapi/profiles/navigation/1.0/verbs/navigated",
    )
    fmt = os.getenv("SVFC_FORMAT", "ndjson")
    log_dir = os.getenv("SVFC_LOGDIR", "logs")

    argv = [
        "main.py",
        "--host", host,
        "--port", str(port),
        "--username", user,
        "--password", pw,
        "--db", db,
        "--coll", coll,
        "--start", start,
        "--end", end,
        "--verb", verb,
        "--format", fmt,
        "--log-dir", log_dir,
        "--fetch-mode", "month",          # ✅ 항상 달마다 쿼리
        "--log-keys-mode", "top",         # ✅ 기본 로그 옵션
        "--log-keys-top-k", "20",
    ]
    return argv


if __name__ == "__main__":
    # 인자가 없으면 기본 스트리밍 실행 인자 구성
    if len(sys.argv) == 1:
        sys.argv = build_default_args()
    cli_main()
