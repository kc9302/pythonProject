# media_verb_flow_check/core/logging_setup.py
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import re

def _verb_name(verb_id: str | None) -> str:
    if not verb_id:
        return "default"
    # 마지막 path segment 추출 후 파일명 안전하게 정제
    name = verb_id.strip("/").split("/")[-1]
    name = name.lower()
    name = re.sub(r"[^a-z0-9._-]+", "_", name)  # 파일명 안전화
    return name or "default"


def setup_logging(
    log_dir: str = "logs",
    level: int = logging.DEBUG,
    verb_id: str | None = None,
):
    """
    기본 로깅 설정:
    - 콘솔 + 회전 파일 로그
    - error_samples, 별도 error 로그 파일 생성 없음
    - 파일명은 verb 별로 분리: media_verb_flow_check_<verb>.log
    """
    log_root = Path(log_dir)
    log_root.mkdir(parents=True, exist_ok=True)

    fname = f"media_verb_flow_check_{_verb_name(verb_id)}.log"

    fmt = logging.Formatter("%(levelname)s:%(name)s:%(message)s")

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(fmt)

    fileh = RotatingFileHandler(
        log_root / fname,
        maxBytes=5_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    fileh.setLevel(level)
    fileh.setFormatter(fmt)

    # noisy 서드파티 억제
    for noisy in ["pymongo", "urllib3", "asyncio", "botocore"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    # 루트 로거 재설정 (중복 방지)
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(console)
    root.addHandler(fileh)

    # 별도 error logger/폴더 생성 안 함
    logging.getLogger("not_object").handlers.clear()
    logging.getLogger("not_object").setLevel(logging.CRITICAL)
