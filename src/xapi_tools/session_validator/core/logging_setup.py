import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logging(log_dir: str = "logs", level: int = logging.DEBUG):
    log_root = Path(log_dir)
    log_root.mkdir(parents=True, exist_ok=True)
    (log_root / "error_samples").mkdir(parents=True, exist_ok=True)  # 에러 샘플 저장 폴더

    fmt = logging.Formatter("%(levelname)s:%(name)s:%(message)s")

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(fmt)

    fileh = RotatingFileHandler(log_root / "session_validator.log",
                                maxBytes=5_000_000, backupCount=3, encoding="utf-8")
    fileh.setLevel(level)
    fileh.setFormatter(fmt)

    # 전용 채널 (extensions not object)
    ext_fileh = RotatingFileHandler(log_root / "session_extensions_not_object.log",
                                    maxBytes=1_000_000, backupCount=2, encoding="utf-8")
    ext_fileh.setLevel(logging.ERROR)
    ext_fileh.setFormatter(fmt)
    ext_logger = logging.getLogger("not_object")
    ext_logger.handlers.clear()
    ext_logger.setLevel(logging.ERROR)
    ext_logger.addHandler(ext_fileh)

    # noisy 서드파티 억제
    for noisy in ["pymongo", "urllib3", "asyncio", "botocore"]:
        logging.getLogger(noisy).setLevel(logging.WARNING)

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(console)
    root.addHandler(fileh)
