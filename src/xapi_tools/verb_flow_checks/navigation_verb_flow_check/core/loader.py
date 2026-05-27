# navigation_verb_flow_check/core/loader.py
import json
from pathlib import Path
from typing import Optional


DEFAULT_CONF = {
    "start": "2024-01",
    "end": "2025-09",
    "verb": "http://lecognizer.com/xapi/profiles/navigation/1.0/verbs/navigated",
}


def load_config(path: Optional[str] = None) -> dict:
    """설정 파일을 로드하거나 기본값을 반환한다."""
    if not path:
        return DEFAULT_CONF.copy()

    p = Path(path)
    if not p.exists():
        return DEFAULT_CONF.copy()

    return json.loads(p.read_text(encoding="utf-8"))
