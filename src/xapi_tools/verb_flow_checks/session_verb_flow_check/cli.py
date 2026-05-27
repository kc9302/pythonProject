# session_verb_flow_check/cli.py
import argparse
import json

from .io.source_iter import (
    iter_mongo_verb_by_month,
    iter_mongo_verb_monthwise,
    VERB_LOGGED_IN,
    SESSION_PROFILE_ID,
)
from .core.monthly_flow_aggregate import aggregate_key_flow_by_month_streaming
from .core.logging_setup import setup_logging
from .core.reporter import write_yearly_key_changes_csv

# 세션 프로파일 기본 verbs (logged-in, logged-out)
SESSION_VERBS = [
    "http://lecognizer.com/xapi/profiles/session/1.0/verbs/logged-in",
    "http://lecognizer.com/xapi/profiles/session/1.0/verbs/logged-out",
    "http://lecognizer.com/xapi/profiles/session/1.0/verbs/timed-out"
]

def main():
    parser = argparse.ArgumentParser(description="Session verb key-flow checker (streaming)")
    parser.add_argument("--host", default="192.168.0.200")
    parser.add_argument("--port", type=int, default=27017)
    parser.add_argument("--username", default="wickedstorm")
    parser.add_argument("--password", default="ws02020!!")
    parser.add_argument("--db", default="lrs")
    parser.add_argument("--coll", default="statements")
    parser.add_argument("--start", default="2024-01")
    parser.add_argument("--end", default="2025-09")
    parser.add_argument("--profile-id", default=SESSION_PROFILE_ID)  # 세션 프로파일 기본
    parser.add_argument("--verb", action="append", default=[], help="분석할 verb (여러 번 지정 가능)")
    parser.add_argument("--verbs", choices=["all"], help="all: 세션 verbs 전체(logged-in, logged-out)")
    parser.add_argument("--fetch-mode", choices=["range", "month"], default="month",
                        help="range: 한방 쿼리 후 월 라벨링 | month: 달마다 쿼리(FETCH 로그 확인용)")
    parser.add_argument("--format", choices=["json", "ndjson"], default="ndjson")
    parser.add_argument("--log-dir", default="logs")
    parser.add_argument("--log-keys-mode", choices=["none", "top", "full"], default="top")
    parser.add_argument("--log-keys-top-k", type=int, default=30)
    parser.add_argument("--out-dir", default="out")
    parser.add_argument("--csv-include-keys", action="store_true")
    parser.add_argument(
        "--required-keys", nargs="*", default=[],
        help="필수 키 목록(공백 구분). 누락 시 WARNING"
    )
    args = parser.parse_args()

    # verb 목록 확정
    verbs = list(args.verb)
    if args.verbs == "all":
        for v in SESSION_VERBS:
            if v not in verbs:
                verbs.append(v)
    if not verbs:
        # 기본값: logged-in만 (기존 호환)
        verbs = [VERB_LOGGED_IN]

    for verb_id in verbs:
        # ✅ verb별로 로그 파일 분리
        setup_logging(log_dir=args.log_dir, verb_id=verb_id or "session")

        common = dict(
            host=args.host, port=args.port, username=args.username, password=args.password,
            db_name=args.db, coll_name=args.coll,
            start_yyyymm=args.start, end_yyyymm=args.end,
            verb_id=verb_id, profile_id=args.profile_id,
        )
        monthed = (
            iter_mongo_verb_monthwise if args.fetch_mode == "month"
            else iter_mongo_verb_by_month
        )(**common)

        # ✅ 스트리밍 집계/검증 (FETCH 직후 A1/A2 로그)
        result = aggregate_key_flow_by_month_streaming(
            monthed_docs=monthed,
            start_yyyymm=args.start,
            end_yyyymm=args.end,
            required_keys=args.required_keys,
            log_keys_mode=args.log_keys_mode,
            log_keys_top_k=args.log_keys_top_k,
        )

        # 출력 (set → list 직렬화)
        if args.format == "json":
            mk = result.get("month_keys", {})
            mk_json = {m: sorted(list(s)) for m, s in mk.items()}
            out = dict(result)
            out["month_keys"] = mk_json
            out["verb"] = verb_id
            print(json.dumps(out, ensure_ascii=False, indent=2))
        else:
            for row in result["results"]:
                row2 = dict(row)
                row2["verb"] = verb_id
                print(json.dumps(row2, ensure_ascii=False))

        # ✅ 연도별 CSV 저장 (파일명에 verb 포함)
        write_yearly_key_changes_csv(
            result["results"],
            out_dir=args.out_dir,
            include_key_lists=args.csv_include_keys,
            verb_id=verb_id or "session",
        )

if __name__ == "__main__":
    main()
