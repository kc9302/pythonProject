# session_verb_flow_check/core/monthly_flow_aggregate.py
from __future__ import annotations
import logging
from typing import Dict, Set, Iterable, Tuple, Optional

from .session_flow import extract_month_and_keys
from .validator import validate_month

log = logging.getLogger(__name__)


def aggregate_key_flow_by_month_streaming(
    monthed_docs: Iterable[Tuple[str, dict]],
    start_yyyymm: str,
    end_yyyymm: str,
    required_keys: Optional[Iterable[str]] = None,
    log_keys_mode: str = "top",    # "none" | "top" | "full"
    log_keys_top_k: int = 30,
):
    """
    입력이 (YYYY-MM, doc) 순서로 들어온다고 가정하고,
    월 경계가 바뀔 때마다 그 달을 즉시 검증/로깅/반환에 누적한다.
    => 각 [FETCH:YYYY-MM] 완료 직후, 해당 달의 A1/A2 로그가 이어지도록 설계.
    """
    def _fmt_list(items: list[str]) -> list[str]:
        if log_keys_mode == "none":
            return []
        if log_keys_mode == "full":
            return items
        return items[:log_keys_top_k]  # top

    results = []
    month_keys: Dict[str, Set[str]] = {}   # 월별 스냅샷 (필요 시)
    prev_keys: Set[str] = set()

    cur_month: Optional[str] = None
    cur_set: Set[str] = set()
    row_count_total = 0
    seen_months: list[str] = []

    def _log_a1_window(prev_mm: str, next_mm: Optional[str], rows: int):
        """예시와 같은 형태의 A1 로그: months=['prev','next'], rows=..."""
        if next_mm:
            months_repr = f"['{prev_mm}','{next_mm}']"
        else:
            months_repr = f"['{prev_mm}']"
        log.debug(f"[A1] 월별 수집 완료: months={months_repr}, rows={rows}")

    def _flush_month(mm: str, s: Set[str], next_month_label: Optional[str], idx: int):
        """현재 달(mm)에 대해 validate + 상세 로그 + results 누적"""
        nonlocal prev_keys

        # A1: 윈도우 로그 (예: ['2024-02','2024-03'])
        _log_a1_window(mm, next_month_label, row_count_total)

        present_sorted = sorted(s)
        res = validate_month(
            month=mm,
            present_keys=s,
            prev_keys=prev_keys,
            required_keys=required_keys,
        )
        results.append(res)
        month_keys[mm] = set(s)  # 스냅샷 보관

        # A2: present/증감 상세 로그
        if log_keys_mode != "none":
            sample_present = _fmt_list(present_sorted)
            suffix = "" if log_keys_mode == "full" else f" (top {len(sample_present)}/{len(present_sorted)})"
            log.debug(f"[A2] {mm} 키 목록{suffix}: {sample_present}")

        if res["added"]:
            added_sorted = res["added"]
            sample_added = _fmt_list(added_sorted)
            suffix = "" if log_keys_mode == "full" else f" (top {len(sample_added)}/{len(added_sorted)})"
            log.debug(f"[A2] {mm} + 추가된 키{suffix}: {sample_added}")

        if res["removed"]:
            removed_sorted = res["removed"]
            sample_removed = _fmt_list(removed_sorted)
            suffix = "" if log_keys_mode == "full" else f" (top {len(sample_removed)}/{len(res['removed'])})"
            log.debug(f"[A2] {mm} - 제거된 키{suffix}: {sample_removed}")

        log.debug(
            f"[A2] {mm} 검증 완료: status={res['status']} "
            f"(present={len(present_sorted)}, added={len(res['added'])}, removed={len(res['removed'])})"
        )

        # 다음 달 비교 기준 갱신
        prev_keys = set(s)

    idx = 1
    pending_next_month: Optional[str] = None  # A1 로그용 '다음 달' 라벨

    for month, doc in monthed_docs:
        if month == "unknown" or month < start_yyyymm or month > end_yyyymm:
            continue

        # 월 경계 감지: 새로운 달 시작 -> 이전 달 flush
        if cur_month is not None and month != cur_month:
            # A1에서 months=['cur_month','month']로 보이도록 next_month_label 전달
            _flush_month(cur_month, cur_set, month, idx)
            idx += 1
            cur_set = set()

        # 현재 달에 누적
        _, keys = extract_month_and_keys(doc)
        if keys:
            cur_set.update(keys)
        cur_month = month

        # 누적 행수 집계 (결과 검증을 위해 총 rows를 계속 업데이트)
        row_count_total += 1

        # 월 시퀀스 기록(보조용)
        if not seen_months or seen_months[-1] != month:
            seen_months.append(month)

    # 마지막 달 flush (다음 달 라벨은 없음)
    if cur_month is not None:
        _flush_month(cur_month, cur_set, None, idx)

    # 반환 구조
    months = [r["month"] for r in results]
    log.debug(f"[ASEND] 스트리밍 수집/검증 완료. 처리문서={row_count_total}, 처리월={len(results)}")
    return {"months": months, "results": results, "month_keys": month_keys}

