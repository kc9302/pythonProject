# assessment_verb_flow_check/core/reporter.py
from __future__ import annotations
import csv
from pathlib import Path
import logging

log = logging.getLogger(__name__)

def _ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _year_of(month_str: str) -> str:
    return month_str[:4]


def write_yearly_key_changes_csv(results, out_dir="out", include_key_lists=True, verb_id=None):
    """
    Navigation 프로파일용
    월별 results 데이터를 받아 연도별 CSV로 저장.
    - include_key_lists=True일 경우 added/removed 키 목록도 포함
    - verb_id가 주어지면 파일명에 verb명(예: navigated-to, navigated-back)을 추가
    """
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # verb_id에서 마지막 segment만 추출 (예: navigated-to)
    verb_name = "unknown"
    if verb_id:
        try:
            verb_name = verb_id.strip("/").split("/")[-1]
        except Exception:
            pass

    # 연도별 묶기
    year_groups = {}
    for r in results:
        year = r["month"][:4]
        year_groups.setdefault(year, []).append(r)

    for year, rows in year_groups.items():
        csv_path = out_path / f"{year}_{verb_name}_changes.csv"  # ✅ verb 추가

        log.debug(f"[REPORT] {csv_path.name} 작성 중 ... ({len(rows)}개월)")

        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            headers = ["month", "status", "present_count", "added_count", "removed_count"]
            if include_key_lists:
                headers += ["added_keys", "removed_keys"]
            writer.writerow(headers)

            for r in rows:
                row = [
                    r["month"],
                    r.get("status", ""),
                    len(r.get("present_keys", [])),
                    len(r.get("added", [])),
                    len(r.get("removed", [])),
                ]
                if include_key_lists:
                    row.append(",".join(r.get("added", [])))
                    row.append(",".join(r.get("removed", [])))
                writer.writerow(row)

        log.debug(f"[REPORT] {csv_path.name} 저장 완료 ({csv_path})")
