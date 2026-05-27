# session_verb_flow_check/core/session_flow.py
from __future__ import annotations
from typing import Set, Tuple, Any

def _get(d: dict, path: str, default=None):
    cur = d
    for key in path.split("."):
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur

def month_label(ts_iso: str) -> str:
    return ts_iso[:7]

# 루트 단위로 수집(extensions에 국한 X)
TARGET_ROOTS = (
    "statement.context",
    "statement.result",
)

def _flatten_keys(obj: Any, prefix: str = "") -> Set[str]:
    """
    obj의 모든 중첩 키를 'dot path'로 평탄화해서 반환.
    - dict: key를 이어붙임
    - list: 인덱스는 쓰지 않고 '[]'를 사용해 경로를 안정화
           (예: contextActivities.category[].id)
    - 원시값: prefix 자체가 키로 간주
    """
    out: Set[str] = set()

    if isinstance(obj, dict):
        # 현재 dict의 1-depth 키들도 기록 (prefix가 있으면 그 다음 depth)
        for k, v in obj.items():
            key_path = f"{prefix}.{k}" if prefix else k
            out.add(key_path)
            out |= _flatten_keys(v, key_path)
        return out

    if isinstance(obj, list):
        # 리스트 자체의 존재도 키로 기록
        list_path = f"{prefix}[]" if prefix else "[]"
        out.add(list_path)
        # 리스트 원소 타입이 dict/리스트이면 하위 키도 계속 평탄화 (경로는 []로 고정)
        for v in obj:
            out |= _flatten_keys(v, list_path)
        return out

    # 스칼라 타입(None/str/int/...) → 더 내려갈 곳이 없으므로 prefix만 키로 간주
    if prefix:
        out.add(prefix)
    return out

def extract_month_and_keys(doc: dict) -> Tuple[str, Set[str]]:
    """
    문서에서 월 라벨과 키 집합을 추출.
    - 월: statement.timestamp(없으면 stored)에서 YYYY-MM
    - 키: statement.context 전체 + statement.result 전체의 모든 중첩 키 경로
          (리스트 인덱스는 []로 정규화)
    """
    ts = _get(doc, "statement.timestamp") or _get(doc, "statement.stored") or doc.get("stored")
    month = month_label(ts) if isinstance(ts, str) and len(ts) >= 7 else "unknown"

    keys: Set[str] = set()
    for root in TARGET_ROOTS:
        node = _get(doc, root)
        if node is not None:
            keys |= _flatten_keys(node, root)

    return month, keys
