import argparse
import sys
from xapi_tools.session_validator import cli as session_validator_cli
from xapi_tools.verb_flow_checks.assessment_verb_flow_check import cli as assessment_flow_cli

def main():
    parser = argparse.ArgumentParser(description="xAPI Tools CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Session Validator Subcommand
    sv_parser = subparsers.add_parser("session-validator", help="Validate xAPI session profiles")
    sv_parser.add_argument("--input-jsonl", required=True, help="xAPI statements jsonl (1 line = 1 doc)")
    sv_parser.add_argument("--start", default="2024-01", help="Start YYYY-MM")
    sv_parser.add_argument("--end", default="2025-09", help="End YYYY-MM")
    sv_parser.add_argument("--out", default="output", help="Output directory")
    sv_parser.add_argument("--logdir", default="logs", help="Log directory")

    # Assessment Flow Check Subcommand
    af_parser = subparsers.add_parser("assessment-flow-check", help="Check assessment verb flows")
    # Add arguments manually for now 
    af_parser.add_argument("--host", default="192.168.0.200")
    af_parser.add_argument("--port", type=int, default=27017)
    af_parser.add_argument("--username", default="wickedstorm")
    af_parser.add_argument("--password", default="ws02020!!")
    af_parser.add_argument("--db", default="lrs")
    af_parser.add_argument("--coll", default="statements")
    af_parser.add_argument("--start", default="2024-01")
    af_parser.add_argument("--end", default="2025-09")
    # For sub-arguments like --verb, we rely on the sub-tool parsing or duplicated args.
    # Duplicating minimal set for help. Ideally we pass remaining args.
    af_parser.add_argument("--verb", action="append", default=[], help="Verbs to analyze")
    af_parser.add_argument("--verbs", choices=["all"], help="Predefined verbs")
    
    # We use parse_known_args to allow sub-tools to parse their own specific args if we wanted,
    # but here we are explicit. Let's add the rest.
    af_parser.add_argument("--fetch-mode", choices=["range", "month"], default="month")
    af_parser.add_argument("--format", choices=["json", "ndjson"], default="ndjson")
    af_parser.add_argument("--log-dir", default="logs")
    af_parser.add_argument("--out-dir", default="out")

    args, unknown = parser.parse_known_args()

    if args.command == "session-validator":
        session_validator_cli.run(args)
    elif args.command == "assessment-flow-check":
        # Pass unknown args too if the sub-tool parser needs them? 
        # But we called run(args) which expects 'args' namespace.
        # So we must ensure 'args' has all attributes.
        # assessment_flow_cli.run(args) relies on args having all attributes.
        # So we really should correct the parser definition above to include all.
        assessment_flow_cli.run(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
