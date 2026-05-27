import logging
from collections import defaultdict, Counter
from pathlib import Path
import json
import csv
from typing import Iterable

log = logging.getLogger(__name__)

total_by_month = defaultdict(int)
errors_by_month = defaultdict(Counter)

# 월별 첫 에러 문서(요약·호환용)
first_error_by_month: dict[str, dict] = {}

# ✅ 월별·카테고리별 첫 문서 샘플
# 예: samples_by_category["2024-02"]["missing"] = {"errors":[...], "doc": {...}}
samples_by_category: dict[str, dict[str, dict]] = defaultdict(dict)


def _classify_error(code: str) -> str:
    if code == "error_extensions_not_object":
        return "structure"
    if code.startswith("error_bad_category"):
        return "category"
    if code.startswith("error_missing"):
        return "missing"
    if "badtype" in code:
        return "type"
    if "badformat" in code or "empty" in code:
        return "format"
    return "other"


def _slim_doc(doc: dict) -> dict:
    """에러 샘플 저장 시 핵심만 추출(개인식별 과도 노출 방지)"""
    stmt = doc.get("statement", {})
    ctx = stmt.get("context", {})
    return {
        "statement.id": stmt.get("id"),
        "statement.timestamp": stmt.get("timestamp"),
        "statement.stored": stmt.get("stored"),
        "context.category": (ctx.get("contextActivities") or {}).get("category"),
        "context.extensions": ctx.get("extensions"),
    }

def aggregate_monthly(
    docs: Iterable[dict],
    rules: dict,
    start_yyyymm: str = "2024-01",
    end_yyyymm: str = "2025-09",
    out_dir: str = "output",
    profile_name: str = "session",
):
    from .session_validate import validate_one

    log = logging.getLogger(__name__)

    # ✅ [1] 헬퍼 함수 정의 (여기에 넣기)
    def _save_month_file(month: str, errors_by_month, first_error_by_month, samples_by_category):
        """월별 결과 파일을 logs/error_samples/<year>/<YYYY-MM>.json 로 저장"""
        code_counts = dict(sorted(errors_by_month.get(month, {}).items()))
        if not code_counts:
            return

        # 카테고리 요약
        cat_counts = {}
        for code, cnt in code_counts.items():
            cat = _classify_error(code)
            cat_counts[cat] = cat_counts.get(cat, 0) + cnt

        # 월별 첫 에러 문서(요약용)
        first = first_error_by_month.get(month, {})
        errors_list = first.get("errors", [])
        doc_slim = first.get("doc", {})

        # 카테고리별 샘플
        cats_map = samples_by_category.get(month, {})
        samples_by_cat_sorted = {cat: cats_map[cat] for cat in sorted(cats_map.keys())}

        # 저장 경로
        year_dir = Path("logs/error_samples") / month[:4]
        year_dir.mkdir(parents=True, exist_ok=True)
        sample_path = year_dir / f"{month}.json"

        payload = {
            "month": month,
            "errors": errors_list,
            "code_summary": code_counts,
            "category_summary": dict(sorted(cat_counts.items())),
            "doc": doc_slim,
            "samples_by_category": samples_by_cat_sorted
        }

        with sample_path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        code_parts = ", ".join(f"{k}={v}" for k, v in code_counts.items()) or "none"
        cat_parts = ", ".join(f"{k}={v}" for k, v in sorted(cat_counts.items())) or "none"
        log.info("[에러 샘플 저장] %s | codes: %s | cats: %s",
                 sample_path, code_parts, cat_parts)

    # ✅ [2] 본 함수 변수 선언
    total_by_month = defaultdict(int)
    errors_by_month = defaultdict(Counter)
    first_error_by_month: dict[str, dict] = {}
    samples_by_category: dict[str, dict[str, dict]] = defaultdict(dict)

    log.debug("[1] 월별 카운트 요약 집계 실행 ...")

    prev_month = None  # 직전 월 추적용

    for doc in docs:
        month, errs = validate_one(doc, rules)

        # 범위 밖이면 스킵
        if month < start_yyyymm or month > end_yyyymm:
            continue

        # ✅ 1️⃣ 월이 바뀌면, 이전 달 파일 저장 + 요약 로그
        if prev_month is not None and month != prev_month:
            # 직전 월 요약
            err_by_code_prev = errors_by_month.get(prev_month, {})
            err_code_parts_prev = ", ".join(f"{k}={v}" for k, v in sorted(err_by_code_prev.items()))
            cat_counts_prev = {}
            for code, cnt in err_by_code_prev.items():
                cat = _classify_error(code)
                cat_counts_prev[cat] = cat_counts_prev.get(cat, 0) + cnt
            cat_parts_prev = ", ".join(f"{k}={v}" for k, v in sorted(cat_counts_prev.items()))

            if err_code_parts_prev:
                log.info("[월별 요약(stream)] %s total=%d | codes: %s | cats: %s",
                         prev_month, total_by_month.get(prev_month, 0),
                         err_code_parts_prev, (cat_parts_prev or "none"))
            else:
                log.info("[월별 요약(stream)] %s total=%d | errors=0",
                         prev_month, total_by_month.get(prev_month, 0))

            # 🔽 직전 달 파일 저장 (에러 요약 + 첫 에러 문서 + 카테고리별 샘플)
            _save_month_file(prev_month, errors_by_month, first_error_by_month, samples_by_category)

        prev_month = month  # 현재 월을 직전 월로 갱신

        # ---- 카운팅/에러 집계 (+카테고리별 첫 캡처)
        total_by_month[month] += 1

        if errs:
            # 1) 에러 코드별 집계
            errors_by_month[month].update(errs)

            # 2) 월별 첫 에러 문서(요약·호환용) 캡처
            if month not in first_error_by_month:
                stmt_id = (doc.get("statement") or {}).get("id")
                first_error_by_month[month] = {
                    "errors": sorted(set(errs)),
                    "doc": _slim_doc(doc),
                }
                log.info("[첫 에러 캡처] %s doc_id=%s | errors: %s",
                         month, stmt_id or "unknown", ", ".join(sorted(set(errs))))

            # 3) 카테고리별 첫 문서 캡처
            cats_this_doc = sorted({_classify_error(code) for code in errs})
            seen_cats = samples_by_category[month].keys()

            new_cats = [c for c in cats_this_doc if c not in seen_cats]
            if new_cats:
                # 이 문서가 새 카테고리(들)의 최초 사례라면, 그 카테고리별로 1건씩 저장
                slim = _slim_doc(doc)
                errors_list = sorted(set(errs))
                for c in new_cats:
                    samples_by_category[month][c] = {
                        "errors": errors_list,
                        "doc": slim,
                    }
                    log.info("[카테고리 캡처] %s cat=%s | doc_id=%s",
                             month, c, (doc.get("statement") or {}).get("id") or "unknown")

    # 루프 종료 후, 마지막 월 요약 한 번 더 찍기
    if prev_month is not None:
        err_by_code_last = errors_by_month.get(prev_month, {})
        err_code_parts_last = ", ".join(f"{k}={v}" for k, v in sorted(err_by_code_last.items()))
        cat_counts_last = {}
        for code, cnt in err_by_code_last.items():
            cat = _classify_error(code)
            cat_counts_last[cat] = cat_counts_last.get(cat, 0) + cnt
        cat_parts_last = ", ".join(f"{k}={v}" for k, v in sorted(cat_counts_last.items()))

        if err_code_parts_last:
            log.info("[월별 요약(stream)] %s total=%d | codes: %s | cats: %s",
                     prev_month, total_by_month.get(prev_month, 0),
                     err_code_parts_last, (cat_parts_last or "none"))
        else:
            log.info("[월별 요약(stream)] %s total=%d | errors=0",
                     prev_month, total_by_month.get(prev_month, 0))
        # 🔽 마지막 달 파일 저장
        _save_month_file(prev_month, errors_by_month, first_error_by_month, samples_by_category)

    log.debug("[1] 완료: %s months", len(total_by_month))

    # 결과 CSV 저장 (연도별 분리)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    columns = rules["report"]["csv_columns"]

    months = sorted(total_by_month.keys())

    # 🔎 프리-요약: CSV 쓰기 전에 월별 요약을 반드시 한 번 찍는다
    for m in months:
        err_by_code = errors_by_month.get(m, {})
        err_code_parts = ", ".join(f"{k}={v}" for k, v in sorted(err_by_code.items()))
        # 카테고리별 집계
        cat_counts = {}
        for code, cnt in err_by_code.items():
            cat = _classify_error(code)
            cat_counts[cat] = cat_counts.get(cat, 0) + cnt
        cat_parts = ", ".join(f"{k}={v}" for k, v in sorted(cat_counts.items()))
        if err_code_parts:
            log.info("[월별 요약(pre)] %s total=%d | codes: %s | cats: %s",
                     m, total_by_month[m], err_code_parts, (cat_parts or "none"))
        else:
            log.info("[월별 요약(pre)] %s total=%d | errors=0", m, total_by_month[m])

    # 연도별 그룹핑
    by_year = defaultdict(list)
    for m in months:
        by_year[m[:4]].append(m)

    for year, mlist in by_year.items():
        csv_path = Path(out_dir) / year / f"{profile_name}_monthly_counts.csv"
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        log.info("[CSV 시작] year=%s, months=%d, path=%s", year, len(mlist), csv_path)

        try:
            with csv_path.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=columns)
                w.writeheader()

                for m in sorted(mlist):
                    # ---- 행 구성
                    row = {c: 0 for c in columns}
                    row["month_label"] = m
                    row["total_statement_count"] = total_by_month.get(m, 0)
                    for err, cnt in errors_by_month.get(m, {}).items():
                        if err in row:
                            row[err] = cnt

                    # ---- 월별 코드/카테고리 요약
                    err_by_code = errors_by_month.get(m, {})
                    err_code_parts = ", ".join(f"{k}={v}" for k, v in sorted(err_by_code.items()))
                    cat_counts = {}
                    for code, cnt in err_by_code.items():
                        cat = _classify_error(code)
                        cat_counts[cat] = cat_counts.get(cat, 0) + cnt
                    cat_parts = ", ".join(f"{k}={v}" for k, v in sorted(cat_counts.items()))

                    # ---- 쓰기 + 로그
                    w.writerow(row)
                    if err_code_parts:
                        log.info("[월별 요약] %s total=%d | codes: %s | cats: %s",
                                 m, row["total_statement_count"], err_code_parts, (cat_parts or "none"))
                    else:
                        log.info("[월별 요약] %s total=%d | errors=0",
                                 m, row["total_statement_count"])

        except Exception as e:
            log.error("[CSV 오류] year=%s path=%s | %s", year, csv_path, e, exc_info=True)
            continue

        log.info("[저장] %s", csv_path.name)

    return total_by_month, errors_by_month
