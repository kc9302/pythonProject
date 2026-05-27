import argparse
from .core.logging_setup import setup_logging
from .core.loader import load_rules
from .core.monthly_aggregate import aggregate_monthly
from .io.source_iter import iter_jsonl

def get_parser():
    ap = argparse.ArgumentParser(description="xAPI Session Validator")
    ap.add_argument("--input-jsonl", required=True, help="xAPI statements jsonl (1 line = 1 doc)")
    ap.add_argument("--start", default="2024-01", help="Start YYYY-MM")
    ap.add_argument("--end", default="2025-09", help="End YYYY-MM")
    ap.add_argument("--out", default="output", help="Output directory")
    ap.add_argument("--logdir", default="logs", help="Log directory")
    return ap

def run(args):
    setup_logging(args.logdir)
    rules = load_rules()
    docs = iter_jsonl(args.input_jsonl)

    aggregate_monthly(docs, rules,
                      start_yyyymm=args.start,
                      end_yyyymm=args.end,
                      out_dir=args.out,
                      profile_name="session")

def main(argv=None):
    ap = get_parser()
    args = ap.parse_args(argv)
    run(args)
