import argparse
import sys
from .common import connect, log, month_date


def main():
    parser = argparse.ArgumentParser(description="NYC TLC local batch pipeline")
    commands = parser.add_subparsers(dest="command",required=True)
    for name in ["ingest", "transform", "export"]:
        sub = commands.add_parser(name)
        sub.add_argument("--month",default="2025-01",type=lambda s:(month_date(s),s)[1])
        if name == "ingest":
            sub.add_argument("--local-file")
        if name == "export":
            sub.add_argument("--require-complete-quarter",action="store_true")
    commands.add_parser("selfcheck")
    args = parser.parse_args()
    try:
        if args.command == "ingest":
            from .ingest import ingest
            ingest(args.month,args.local_file)
        elif args.command == "transform":
            from .transform import transform
            transform(args.month)
        elif args.command == "export":
            from .export import export
            export(args.month,args.require_complete_quarter)
        else:
            with connect() as conn:
                rows=conn.execute("SELECT source_month,raw_rows,accepted_rows,rejected_rows FROM taxi.sources ORDER BY source_month").fetchall()
                if not rows:
                    raise ValueError("No processed sources found")
                for month,raw,accepted,rejected in rows:
                    if accepted is None or raw != accepted + rejected:
                        raise ValueError(f"Reconciliation failed for {month}")
                log("selfcheck_passed", sources=len(rows))
    except Exception as error:
        # Do not log connection strings or secrets.
        log("pipeline_failed",stage=args.command,error_type=type(error).__name__)
        print("Stage failed. Check database health, source schema and month completeness; see README troubleshooting.",file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
