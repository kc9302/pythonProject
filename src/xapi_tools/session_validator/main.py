# main.py
import os
import sys
import argparse
from pathlib import Path

# 로컬 패키지 임포트 편의
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from xapi_tools.session_validator.core.logging_setup import setup_logging
from xapi_tools.session_validator.core.loader import load_rules
from xapi_tools.session_validator.core.monthly_aggregate import aggregate_monthly
from xapi_tools.session_validator.io.source_iter import iter_jsonl, iter_mongo


# ---- 기본값(인자 없이 실행 시 사용) ----
DEFAULT_START = "2024-01"
DEFAULT_END = "2025-09"
DEFAULT_OUT = "output"
DEFAULT_LOGDIR = "logs"

# Mongo 기본 접속값 (환경변수로도 덮어쓰기 가능)
DEFAULT_MONGO = {
    "host": os.getenv("MONGO_HOST", "192.168.0.200"),
    "port": int(os.getenv("MONGO_PORT", "27017")),
    "username": os.getenv("MONGO_USER", "wickedstorm"),
    "password": os.getenv("MONGO_PASS", "ws02020!!"),
    "db_name": os.getenv("MONGO_DB", "lrs"),
    "coll_name": os.getenv("MONGO_COLL", "statements"),
}


def build_arg_parser():
    ap = argparse.ArgumentParser(
        description="xAPI Session Profile 정합성 검증 (월별 집계)",
        add_help=True,
    )
    # 공통 옵션 (미지정 시 기본값 사용)
    ap.add_argument("--start", default=DEFAULT_START, help=f"시작 YYYY-MM (default: {DEFAULT_START})")
    ap.add_argument("--end", default=DEFAULT_END, help=f"종료 YYYY-MM (default: {DEFAULT_END})")
    ap.add_argument("--out", default=DEFAULT_OUT, help=f"결과 출력 디렉터리 (기본: {DEFAULT_OUT})")
    ap.add_argument("--logdir", default=DEFAULT_LOGDIR, help=f"로그 디렉터리 (기본: {DEFAULT_LOGDIR})")

    # 입력 소스 선택 (둘 다 미지정 시 자동으로 Mongo 사용)
    ap.add_argument("--use-mongo", action="store_true", help="MongoDB에서 직접 조회")
    ap.add_argument("--input-jsonl", help="xAPI statements jsonl (한 줄당 한 문서)")

    # Mongo 파라미터 (미지정 시 DEFAULT_MONGO 사용)
    ap.add_argument("--mongo-host")
    ap.add_argument("--mongo-port", type=int)
    ap.add_argument("--mongo-user")
    ap.add_argument("--mongo-pass")
    ap.add_argument("--mongo-db")
    ap.add_argument("--mongo-coll")

    return ap


def resolve_mongo_args(args) -> dict:
    # 인자로 들어온 값이 있으면 그것을, 없으면 DEFAULT_MONGO 사용
    return {
        "host": args.mongo_host or DEFAULT_MONGO["host"],
        "port": args.mongo_port or DEFAULT_MONGO["port"],
        "username": args.mongo_user or DEFAULT_MONGO["username"],
        "password": args.mongo_pass or DEFAULT_MONGO["password"],
        "db_name": args.mongo_db or DEFAULT_MONGO["db_name"],
        "coll_name": args.mongo_coll or DEFAULT_MONGO["coll_name"],
    }


def main():
    ap = build_arg_parser()
    # 인자가 하나도 없을 때도 파싱 가능하도록 함
    args = ap.parse_args(args=None if len(sys.argv) > 1 else [])

    # 로깅 준비
    setup_logging(args.logdir)

    rules = load_rules()

    # ---- 소스 자동 결정 로직 ----
    # 1) --use-mongo 지정 시 → Mongo
    # 2) --input-jsonl 지정 시 → JSONL
    # 3) 아무것도 지정 안 했을 때 → Mongo (요청사항)
    use_mongo = args.use_mongo or (not args.input_jsonl)

    if use_mongo:
        margs = resolve_mongo_args(args)
        docs = iter_mongo(
            host=margs["host"],
            port=margs["port"],
            username=margs["username"],
            password=margs["password"],
            db_name=margs["db_name"],
            coll_name=margs["coll_name"],
            start_yyyymm=args.start,
            end_yyyymm=args.end,
        )
    else:
        docs = iter_jsonl(args.input_jsonl)

    aggregate_monthly(
        docs,
        rules,
        start_yyyymm=args.start,
        end_yyyymm=args.end,
        out_dir=args.out,
        profile_name="session",
    )


if __name__ == "__main__":
    main()
