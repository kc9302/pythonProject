# navigation_verb_flow_check/core/flow.py
from __future__ import annotations
from typing import Dict, List, Set, Tuple


TARGET_PATHS = (
    ("statement", "context", "extensions"),
    ("statement", "result", "extensions"),
)


def _dig(d: dict, path: Tuple[str, ...]):
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return None
        cur = cur[k]
    return cur


def collect_monthly_keys(monthed_docs: list[tuple[str, dict]]) -> Dict[str, Set[str]]:
    """월별로 extensions 키를 수집한다."""
    month_keys: Dict[str, Set[str]] = {}
    for month, doc in monthed_docs:
        keys = month_keys.setdefault(month, set())
        for path in TARGET_PATHS:
            node = _dig(doc, path)
            if isinstance(node, dict):
                keys.update(node.keys())
    return month_keys


def compute_key_spans(month_keys: Dict[str, Set[str]]) -> Dict[str, dict]:
    """각 키의 최초/최종 등장 월과 존재 월 목록을 계산한다."""
    spans: Dict[str, dict] = {}
    for month in sorted(month_keys.keys()):
        for key in month_keys[month]:
            if key not in spans:
                spans[key] = {
                    "first_seen": month,
                    "last_seen": month,
                    "months_present": {month},
                }
            else:
                spans[key]["last_seen"] = month
                spans[key]["months_present"].add(month)
    return spans


def diff_month(month_keys: Dict[str, Set[str]], month: str, prev_month: str | None) -> dict:
    """두 달 사이의 키 증감(diff)을 계산한다."""
    present = month_keys.get(month, set())
    prev = month_keys.get(prev_month, set()) if prev_month else set()
    return {
        "month": month,
        "present_count": len(present),
        "added": sorted(present - prev),
        "removed": sorted(prev - present),
    }


def month_sequence(start_yyyymm: str, end_yyyymm: str) -> List[str]:
    """YYYY-MM 범위의 월 시퀀스 리스트를 생성한다."""
    y, m = map(int, start_yyyymm.split("-"))
    ye, me = map(int, end_yyyymm.split("-"))
    out = []
    while (y, m) <= (ye, me):
        out.append(f"{y:04d}-{m:02d}")
        if m == 12:
            y += 1
            m = 1
        else:
            m += 1
    return out


def build_monthly_report(month_keys: Dict[str, Set[str]], start_yyyymm: str, end_yyyymm: str) -> List[dict]:
    """월별 증감 리포트를 생성한다."""
    months = month_sequence(start_yyyymm, end_yyyymm)
    report = []
    prev = None
    for mm in months:
        report.append(diff_month(month_keys, mm, prev))
        prev = mm
    return report
