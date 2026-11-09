"""Check published snapshot hashes and reconcile monthly aggregates."""
import csv
import json
from pathlib import Path
import sys

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from taxi.common import checksum
output=root/'outputs'
pointer=json.loads((output/'latest.json').read_text())
snapshot=output/pointer['snapshot']
manifest=json.loads((snapshot/'manifest.json').read_text())
for name,metadata in manifest['files'].items():
    if checksum(snapshot/name)!=metadata['sha256']:
        raise SystemExit('Checksum failed: '+name)
source=next(s for s in manifest['sources'] if s['month']==manifest['month'])
if source['raw_rows']!=source['accepted_rows']+source['rejected_rows']:
    raise SystemExit('Source counts do not reconcile')
for name in ['hourly_features.csv','daily_summary.csv']:
    with (snapshot/name).open() as f:
        total=sum(int(row['trip_count']) for row in csv.DictReader(f))
    if total!=source['accepted_rows']:
        raise SystemExit('Aggregate counts do not reconcile: '+name)
with (snapshot/'quality_report.csv').open() as f:
    rejected=sum(int(row['row_count']) for row in csv.DictReader(f))
if rejected!=source['rejected_rows']:
    raise SystemExit('Quality report does not reconcile')
with (snapshot/'quarterly_features.csv').open() as f:
    quarter_total=sum(int(row['trip_count']) for row in csv.DictReader(f))
if quarter_total!=sum(s['accepted_rows'] for s in manifest['sources']):
    raise SystemExit('Quarterly trip total does not reconcile')
print('PASS: snapshot hashes, raw/accepted/rejected counts, rejection reasons and monthly/quarterly trip totals')
print('Quarter complete:',manifest['complete_quarter'])
