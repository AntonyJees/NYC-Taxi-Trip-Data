import json
import os
from pathlib import Path
import shutil
import time
import urllib.request
import uuid
import pyarrow.parquet as pq
from psycopg.types.json import Jsonb
from .common import atomic_json, checksum, connect, log, month_date

COLUMNS = ["tpep_pickup_datetime", "tpep_dropoff_datetime", "trip_distance", "fare_amount", "total_amount", "passenger_count", "PULocationID", "DOLocationID"]


def inspect(path, minimum_rows):
    file = pq.ParquetFile(path)
    missing = sorted(set(COLUMNS) - set(file.schema_arrow.names))
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    if file.metadata.num_rows < minimum_rows:
        raise ValueError(f"Source has {file.metadata.num_rows} rows; minimum is {minimum_rows}")
    return file


def acquire(month, local_file=None, minimum_rows=1_000_000):
    month_date(month)
    raw = Path(os.environ.get("DATA_DIR", "data/raw"))
    raw.mkdir(parents=True, exist_ok=True)
    target = raw / f"yellow_tripdata_{month}.parquet"
    url = f"https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_{month}.parquet"
    if local_file:
        # The explicit local path is useful for an official file downloaded offline.
        if Path(local_file).resolve() != target.resolve():
            tmp = target.with_suffix(".part")
            shutil.copyfile(local_file, tmp)
            inspect(tmp, minimum_rows)
            os.replace(tmp, target)
    elif not target.exists():
        tmp = target.with_suffix(".part")
        for attempt in range(3):
            try:
                with urllib.request.urlopen(url, timeout=120) as source, open(tmp, "wb") as out:
                    shutil.copyfileobj(source, out, 1024 * 1024)
                inspect(tmp, minimum_rows)
                os.replace(tmp, target)
                break
            except Exception:
                tmp.unlink(missing_ok=True)
                if attempt == 2:
                    raise
                time.sleep(2 ** attempt)
    file = inspect(target, minimum_rows)
    sha = checksum(target)
    manifest_path = target.with_suffix(".json")
    if manifest_path.exists() and not local_file:
        previous = json.loads(manifest_path.read_text())
        if previous["sha256"] != sha:
            raise ValueError("Cached source checksum changed; restore or explicitly re-ingest the official file")
    manifest = {"source_url": url, "month": month, "sha256": sha,
                "raw_rows": file.metadata.num_rows, "bytes": target.stat().st_size,
                "columns": file.schema_arrow.names, "schema_version": 1}
    atomic_json(manifest_path, manifest)
    return target, manifest


def ingest(month, local_file=None, minimum_rows=1_000_000):
    start = time.perf_counter()
    date = month_date(month)
    rownum = 0
    with connect() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(19014)::text")
        target, manifest = acquire(month, local_file, minimum_rows)
        conn.execute("CREATE TEMP TABLE raw_stage (LIKE taxi.raw_trips INCLUDING DEFAULTS) ON COMMIT DROP")
        with conn.cursor().copy("COPY raw_stage FROM STDIN") as copy:
            for batch in pq.ParquetFile(target).iter_batches(batch_size=100_000, columns=COLUMNS):
                arrays = [batch.column(i).to_pylist() for i in range(len(COLUMNS))]
                for row in zip(*arrays):
                    rownum += 1
                    copy.write_row((date, rownum, *row))
        if rownum != manifest["raw_rows"]:
            raise ValueError("Streamed row count differs from Parquet metadata")
        conn.execute("DELETE FROM taxi.raw_trips WHERE source_month=%s", (date,))
        conn.execute("INSERT INTO taxi.raw_trips SELECT * FROM raw_stage")
        conn.execute("""INSERT INTO taxi.sources(source_month,source_url,sha256,raw_rows)
          VALUES (%s,%s,%s,%s) ON CONFLICT(source_month) DO UPDATE SET
          source_url=excluded.source_url, sha256=excluded.sha256, raw_rows=excluded.raw_rows,
          loaded_at=now(), transformed_sha256=NULL, accepted_rows=NULL, rejected_rows=NULL,
          transformed_at=NULL, transform_seconds=NULL""", (date, manifest["source_url"], manifest["sha256"], rownum))
        metrics = {**manifest, "seconds": round(time.perf_counter()-start, 3)}
        conn.execute("INSERT INTO taxi.runs(run_id,stage,source_month,metrics) VALUES (%s,'ingest',%s,%s)",
                     (str(uuid.uuid4()), date, Jsonb(metrics)))
    log("ingest_complete", **metrics)
    return metrics
