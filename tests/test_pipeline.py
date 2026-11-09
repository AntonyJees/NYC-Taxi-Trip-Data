"""Run unit tests anywhere; set TEST_PG=1 against a disposable test database for integration tests."""
import datetime as dt
import json
import os
from pathlib import Path
import math
import pytest
import pyarrow as pa
import pyarrow.parquet as pq
from taxi.common import month_date, checksum, connect
from taxi.ingest import COLUMNS, acquire, inspect, ingest
from taxi.transform import transform
from taxi.export import export


def fixture_file(path):
    pickup=dt.datetime(2025,1,1,12)
    base=[pickup,pickup+dt.timedelta(minutes=10),2.,10.,12.,1.,10,20]
    rows=[base.copy(),base.copy()] # identical trips retained; no trip identifier exists
    for index,value in [(0,None),(0,dt.datetime(2024,12,31)),(1,pickup),(2,-1.),(3,float('nan')),(4,float('inf')),(6,999)]:
        row=base.copy();row[index]=value;rows.append(row)
    row=base.copy();row[5]=None;rows.append(row)
    schema=pa.schema([(COLUMNS[0],pa.timestamp('us')),(COLUMNS[1],pa.timestamp('us')),
        *[(x,pa.float64()) for x in COLUMNS[2:6]],*[(x,pa.int32()) for x in COLUMNS[6:]]])
    pq.write_table(pa.Table.from_pylist([dict(zip(COLUMNS,r)) for r in rows],schema=schema),path)
    return len(rows)


@pytest.mark.parametrize('value',['2025-00','2025-13','25-01','2025-1','2025-01;DROP TABLE taxi.sources','../../2025-01'])
def test_month_rejects_invalid_input(value):
    with pytest.raises(ValueError):month_date(value)


def test_month_valid():
    assert month_date('2025-01')==dt.date(2025,1,1)


def test_minimum_and_schema(tmp_path):
    path=tmp_path/'source.parquet';fixture_file(path)
    with pytest.raises(ValueError,match='minimum'):inspect(path,1_000_000)
    pq.write_table(pa.table({'wrong':[1]}),path)
    with pytest.raises(ValueError,match='Missing'):inspect(path,0)


def test_checksum_tampering(tmp_path,monkeypatch):
    source=tmp_path/'source.parquet';fixture_file(source)
    monkeypatch.setenv('DATA_DIR',str(tmp_path/'raw'))
    path,manifest=acquire('2025-01',source,0)
    manifest_path=path.with_suffix('.json')
    manifest['sha256']='0'*64
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match='checksum'):acquire('2025-01',minimum_rows=0)


@pytest.mark.skipif(os.getenv('TEST_PG')!='1',reason='Needs a disposable PostgreSQL database')
def test_integration_quality_idempotency_and_exports(tmp_path,monkeypatch):
    path=tmp_path/'source.parquet';n=fixture_file(path)
    monkeypatch.setenv('DATA_DIR',str(tmp_path/'raw'))
    monkeypatch.setenv('OUTPUT_DIR',str(tmp_path/'outputs'))
    ingest('2025-01',path,0)
    result=transform('2025-01')
    assert result['raw_rows']==n
    assert result['accepted_rows']==3
    assert result['rejected_rows']==7
    # Running each stage again replaces the source partition rather than appending rows.
    ingest('2025-01',path,0)
    with pytest.raises(ValueError,match='transformed'):export('2025-01')
    assert transform('2025-01')['accepted_rows']==3
    manifest=export('2025-01')
    assert manifest['complete_quarter'] is False
    for name,meta in manifest['files'].items():
        assert checksum(tmp_path/'outputs'/manifest['run_id']/name)==meta['sha256']
    with pytest.raises(ValueError,match='incomplete'):export('2025-01',True)
    import csv
    with open(tmp_path/'outputs'/manifest['run_id']/'hourly_features.csv') as f:
        rows=list(csv.DictReader(f))
    assert len(rows)==1 and int(rows[0]['trip_count'])==3
    assert math.isclose(float(rows[0]['mean_total_amount']),12.)
    with connect() as conn:
        assert conn.execute('SELECT count(*) FROM taxi.raw_trips').fetchone()[0]==n
        before=conn.execute('SELECT count(*) FROM taxi.clean_trips').fetchone()[0]
    # Test database transaction rollback independently of the pipeline's success path.
    with pytest.raises(RuntimeError):
        with connect() as conn:
            conn.execute('DELETE FROM taxi.clean_trips')
            raise RuntimeError('simulated failure')
    with connect() as conn:
        assert conn.execute('SELECT count(*) FROM taxi.clean_trips').fetchone()[0]==before
    # Complete-quarter path: two additional sources, without simulating them as real TLC data.
    for month in ['2025-02','2025-03']:
        ingest(month,path,0)
        transform(month) # January pickups are correctly rejected for February and March
    assert export('2025-03',True)['complete_quarter'] is True

