import time
import uuid
from psycopg.types.json import Jsonb
from .common import connect, log, month_date


def transform(month):
    start = time.perf_counter()
    date = month_date(month)
    with connect() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(19014)::text")
        source = conn.execute("SELECT raw_rows, sha256 FROM taxi.sources WHERE source_month=%s FOR UPDATE", (date,)).fetchone()
        if source is None:
            raise ValueError("Ingest this month before transformation")
        conn.execute("DELETE FROM taxi.clean_trips WHERE source_month=%s", (date,))
        conn.execute("""INSERT INTO taxi.clean_trips SELECT source_month,source_row,pickup_at,dropoff_at,
          trip_distance,fare_amount,total_amount,passenger_count,pickup_zone,dropoff_zone
          FROM taxi.classified WHERE source_month=%s AND reject_reason IS NULL""", (date,))
        conn.execute("DELETE FROM taxi.rejections WHERE source_month=%s", (date,))
        conn.execute("""INSERT INTO taxi.rejections SELECT source_month,reject_reason,count(*)
          FROM taxi.classified WHERE source_month=%s AND reject_reason IS NOT NULL GROUP BY 1,2""", (date,))
        accepted = conn.execute("SELECT count(*) FROM taxi.clean_trips WHERE source_month=%s", (date,)).fetchone()[0]
        rejected = conn.execute("SELECT COALESCE(sum(row_count),0) FROM taxi.rejections WHERE source_month=%s", (date,)).fetchone()[0]
        if accepted + rejected != source[0]:
            raise ValueError("Reconciliation failed: raw must equal accepted plus rejected")
        seconds = round(time.perf_counter()-start, 3)
        conn.execute("""UPDATE taxi.sources SET transformed_sha256=sha256, accepted_rows=%s,
          rejected_rows=%s,transform_seconds=%s,transformed_at=now() WHERE source_month=%s""", (accepted,rejected,seconds,date))
        metrics = {"month": month, "raw_rows": source[0], "sha256": source[1], "accepted_rows": accepted,
                   "rejected_rows": int(rejected), "seconds": seconds}
        conn.execute("INSERT INTO taxi.runs(run_id,stage,source_month,metrics) VALUES (%s,'transform',%s,%s)",
                     (str(uuid.uuid4()),date,Jsonb(metrics)))
    log("transform_complete", **metrics)
    return metrics
