import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re


def month_date(value):
    if not re.fullmatch(r"20\d{2}-(0[1-9]|1[0-2])", value):
        raise ValueError("Month must be YYYY-MM between 2000 and 2099")
    return dt.date.fromisoformat(value + "-01")


def connect():
    import psycopg
    return psycopg.connect(connect_timeout=15, application_name="nyc_taxi_phase2")


def checksum(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def atomic_json(path, value):
    path = Path(path)
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_text(json.dumps(value, indent=2, default=str) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def log(event, **fields):
    print(json.dumps({"time": dt.datetime.now(dt.timezone.utc).isoformat(), "event": event, **fields}, default=str), flush=True)
