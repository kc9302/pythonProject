# assessment_verb_flow_check/core/validator.py
from __future__ import annotations
import logging
from typing import Iterable, Set, Dict

log = logging.getLogger(__name__)


def validate_month(
    month: str,
    present_keys: Set[str],
    prev_keys: Set[str] | None = None,
    required_keys: Iterable[str] | None = None,
) -> Dict:
    """
    한 달 단위 검증:
    - added / removed: 전월 대비 증감
    - missing_required: 필수 키 누락
    """
    prev_keys = prev_keys or set()
    required = set(required_keys) if required_keys else set()

    added = sorted(present_keys - prev_keys)
    removed = sorted(prev_keys - present_keys)
    missing_required = sorted(required - present_keys)

    # 상세 로그
    log.debug(
        f"[M] {month} 수집/검증 | present:{len(present_keys)} added:{len(added)} removed:{len(removed)}"
    )
    if added:
        log.debug(f"    + 추가된 키: {added}")
    if removed:
        log.debug(f"    - 제거된 키: {removed}")
    if missing_required:
        log.warning(f"    ! 필수 키 누락: {missing_required}")

    status = "ok" if not missing_required else "missing-required"
    return {
        "month": month,
        "present_count": len(present_keys),
        "added": added,
        "removed": removed,
        "missing_required": missing_required,
        "status": status,
    }
