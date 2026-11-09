import datetime as dt
import os
from pathlib import Path
import shutil
import uuid
from psycopg import sql
from .common import atomic_json, checksum, connect, log, month_date


def export(month, require_complete_quarter=False):
    date = month_date(month)
    quarter = date.replace(month=((date.month-1)//3)*3+1)
    expected = [quarter.replace(month=quarter.month+i) for i in range(3)]
    quarter_end = dt.date(quarter.year+1,1,1) if quarter.month == 10 else quarter.replace(month=quarter.month+3)
    root = Path(os.environ.get("OUTPUT_DIR", "outputs"))
    root.mkdir(parents=True, exist_ok=True)
    run_id = str(uuid.uuid4())
    staging = root / (".staging-" + run_id)
    staging.mkdir()
    try:
        with connect() as conn:
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY")
            sources = conn.execute("""SELECT source_month,sha256,transformed_sha256,raw_rows,accepted_rows,rejected_rows
              FROM taxi.sources WHERE source_month >= %s AND source_month < %s ORDER BY source_month""", (quarter,quarter_end)).fetchall()
            if not sources or date not in [s[0] for s in sources] or any(s[1] != s[2] for s in sources):
                raise ValueError("Every loaded month in this quarter must be transformed before export")
            complete = [s[0] for s in sources] == expected
            if require_complete_quarter and not complete:
                raise ValueError("Quarter is incomplete; ingest and transform all three months")
            exports = {
              "hourly_features.csv": ("SELECT * FROM taxi.hourly_features WHERE source_month = {} ORDER BY pickup_hour,pickup_zone", date),
              "daily_summary.csv": ("SELECT * FROM taxi.daily_summary WHERE source_month = {} ORDER BY pickup_date", date),
              "quarterly_features.csv": ("SELECT * FROM taxi.quarterly_features WHERE quarter_start = {} ORDER BY pickup_zone,hour_of_day", quarter),
              "quality_report.csv": ("SELECT * FROM taxi.rejections WHERE source_month = {} ORDER BY reason", date),
            }
            files = {}
            for name,(query,value) in exports.items():
                statement = sql.SQL("COPY ({}) TO STDOUT WITH (FORMAT CSV, HEADER TRUE)").format(sql.SQL(query).format(sql.Literal(value)))
                path = staging / name
                with conn.cursor().copy(statement) as copy, open(path,"wb") as f:
                    for block in copy:
                        f.write(block)
                files[name] = {"sha256": checksum(path), "bytes": path.stat().st_size}
            manifest = {"run_id": run_id, "month": month, "quarter_start": str(quarter),
              "complete_quarter": complete, "expected_months": [str(x)[:7] for x in expected],
              "available_months": [str(s[0])[:7] for s in sources], "timestamp_basis": "NYC local wall time, as supplied by TLC",
              "sources": [{"month":str(s[0])[:7],"sha256":s[1],"raw_rows":s[3],"accepted_rows":s[4],"rejected_rows":s[5]} for s in sources],
              "files": files, "created_at":dt.datetime.now(dt.timezone.utc).isoformat()}
            atomic_json(staging / "manifest.json", manifest)
        destination = root / run_id
        os.replace(staging, destination)
        atomic_json(root / "latest.json", {"snapshot": run_id, "month": month})
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    log("export_complete", snapshot=str(destination), complete_quarter=complete)
    return manifest
