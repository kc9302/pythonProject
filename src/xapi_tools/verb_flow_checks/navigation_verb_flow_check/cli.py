# navigation_verb_flow_check/cli.py
import argparse
import json

from .io.source_iter import (
    iter_mongo_verb_by_month,     # 한방(range) 쿼리 후 코드에서 월 라벨링
    iter_mongo_verb_monthwise,    # 달마다 쿼리(FETCH 로그 확인용)
    VERB_NAVIGATED,
)
from .core.monthly_flow_aggregate import (
    aggregate_key_flow_by_month_streaming,  # 스트리밍 전용 사용
)
from .core.logging_setup import setup_logging
from .core.reporter import write_yearly_key_changes_csv  # ✅ 추가


def main():
    parser = argparse.ArgumentParser(description="Navigation verb key-flow checker (streaming-only)")
    parser.add_argument("--host", default="192.168.0.200")
    parser.add_argument("--port", type=int, default=27017)
    parser.add_argument("--username", default="wickedstorm")
    parser.add_argument("--password", default="ws02020!!")
    parser.add_argument("--db", default="lrs")
    parser.add_argument("--coll", default="statements")
    parser.add_argument("--start", default="2024-01")
    parser.add_argument("--end", default="2025-09")
    parser.add_argument("--verb", default=VERB_NAVIGATED)
    parser.add_argument("--format", choices=["json", "ndjson"], default="json")
    parser.add_argument("--log-dir", default="logs")

    # 월별 키 목록/증감 로그 옵션
    parser.add_argument(
        "--log-keys-mode",
        choices=["none", "top", "full"],
        default="top",
        help="월별 키/증감 로그 출력 모드 (none|top|full). 기본: top",
    )
    parser.add_argument(
        "--log-keys-top-k",
        type=int,
        default=30,
        help="log-keys-mode=top일 때 상위 몇 개 키를 출력할지. 기본: 30",
    )

    # 가져오기 방식
    parser.add_argument(
        "--fetch-mode",
        choices=["range", "month"],
        default="range",
        help="문서 가져오기 방식: range(한방 쿼리) | month(달마다 쿼리; FETCH 로그 확인용)",
    )

    # 필수 키 검사
    parser.add_argument(
        "--required-keys",
        nargs="*",
        default=[],
        help="필수 키 목록(공백 구분). 누락 시 WARNING",
    )

    args = parser.parse_args()
    setup_logging(log_dir=args.log_dir, verb_id=args.verb)  # ✅ verb_id 전달

    # 입력 제너레이터 선택
    if args.fetch_mode == "month":
        monthed = iter_mongo_verb_monthwise(
            host=args.host,
            port=args.port,
            username=args.username,
            password=args.password,
            db_name=args.db,
            coll_name=args.coll,
            start_yyyymm=args.start,
            end_yyyymm=args.end,
            verb_id=args.verb,
        )
    else:
        monthed = iter_mongo_verb_by_month(
            host=args.host,
            port=args.port,
            username=args.username,
            password=args.password,
            db_name=args.db,
            coll_name=args.coll,
            start_yyyymm=args.start,
            end_yyyymm=args.end,
            verb_id=args.verb,
        )

    # ✅ 스트리밍 집계/검증 (FETCH 직후 A1/A2 로그가 붙어서 출력됨)
    result = aggregate_key_flow_by_month_streaming(
        monthed_docs=monthed,
        start_yyyymm=args.start,
        end_yyyymm=args.end,
        required_keys=args.required_keys,
        log_keys_mode=args.log_keys_mode,
        log_keys_top_k=args.log_keys_top_k,
    )

    # 출력
    if args.format == "json":
        # month_keys의 set을 list로 변환
        mk = result.get("month_keys", {})
        mk_json = {month: sorted(list(keys)) for month, keys in mk.items()}
        out = dict(result)
        out["month_keys"] = mk_json
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        for row in result["results"]:
            print(json.dumps(row, ensure_ascii=False))

    # ✅ 결과 CSV 저장 (연도별 out/ 폴더에)
    write_yearly_key_changes_csv(
        result["results"],
        out_dir="out",
        include_key_lists=True,
        verb_id=args.verb,  # ✅ verb 전달
    )

if __name__ == "__main__":
    main()
