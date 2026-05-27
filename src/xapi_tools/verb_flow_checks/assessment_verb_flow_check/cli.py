# assessment_verb_flow_check/cli.py
import argparse
import json

from .io.source_iter import (
    iter_mongo_verb_by_month,
    iter_mongo_verb_monthwise,
    DEFAULT_ASSESSMENT_PROFILE_ID,
)
from .core.monthly_flow_aggregate import aggregate_key_flow_by_month_streaming
from .core.logging_setup import setup_logging
from .core.reporter import write_yearly_key_changes_csv

ASSESSMENT_VERBS = [
    "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/started",
    "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/stopped",
    "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/resumed",
    "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/restarted",
    "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/submitted",
    "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/skipped",
    "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/completed",
    "http://lecognizer.com/xapi/profiles/assessment/1.0/verbs/timed-out"
]

def get_parser():
    p = argparse.ArgumentParser(description="Assessment verb key-flow checker (streaming)")
    p.add_argument("--host", default="192.168.0.200")
    p.add_argument("--port", type=int, default=27017)
    p.add_argument("--username", default="wickedstorm")
    p.add_argument("--password", default="ws02020!!")
    p.add_argument("--db", default="lrs")
    p.add_argument("--coll", default="statements")
    p.add_argument("--start", default="2024-01")
    p.add_argument("--end", default="2025-09")
    p.add_argument("--profile-id", default=DEFAULT_ASSESSMENT_PROFILE_ID)
    p.add_argument("--verb", action="append", default=[], help="분석할 verb (여러 번 지정 가능)")
    p.add_argument("--verbs", choices=["all"], help="all: 미리 정의된 assessment verbs 전체")
    p.add_argument("--fetch-mode", choices=["range", "month"], default="month")
    p.add_argument("--format", choices=["json", "ndjson"], default="ndjson")
    p.add_argument("--log-dir", default="logs")
    p.add_argument("--log-keys-mode", choices=["none","top","full"], default="top")
    p.add_argument("--log-keys-top-k", type=int, default=30)
    p.add_argument("--out-dir", default="out")
    p.add_argument("--csv-include-keys", action="store_true")
    return p

def run(args):
    # verb 목록 확정
    verbs = list(args.verb)
    if args.verbs == "all":
        for v in ASSESSMENT_VERBS:
            if v not in verbs:
                verbs.append(v)
    if not verbs:
        verbs = [""]  # 빈 문자열: verb 필터 없이 profile 전체

    for verb_id in verbs:
        setup_logging(log_dir=args.log_dir, verb_id=verb_id or "assessment")

        common = dict(
            host=args.host, port=args.port, username=args.username, password=args.password,
            db_name=args.db, coll_name=args.coll,
            start_yyyymm=args.start, end_yyyymm=args.end,
            verb_id=verb_id, profile_id=args.profile_id,
        )
        monthed = (iter_mongo_verb_monthwise if args.fetch_mode == "month" else iter_mongo_verb_by_month)(**common)

        result = aggregate_key_flow_by_month_streaming(
            monthed_docs=monthed,
            start_yyyymm=args.start, end_yyyymm=args.end,
            required_keys=[], log_keys_mode=args.log_keys_mode, log_keys_top_k=args.log_keys_top_k,
        )

        if args.format == "json":
            mk = result.get("month_keys", {})
            mk_json = {m: sorted(list(s)) for m, s in mk.items()}
            out = dict(result); out["month_keys"] = mk_json; out["verb"] = verb_id
            print(json.dumps(out, ensure_ascii=False, indent=2))
        else:
            for row in result["results"]:
                row2 = dict(row); row2["verb"] = verb_id
                print(json.dumps(row2, ensure_ascii=False))

        write_yearly_key_changes_csv(
            result["results"],
            out_dir=args.out_dir,
            include_key_lists=args.csv_include_keys,
            verb_id=verb_id or "assessment",
        )

def main(argv=None):
    p = get_parser()
    args = p.parse_args(argv)
    run(args)

if __name__ == "__main__":
    main()
