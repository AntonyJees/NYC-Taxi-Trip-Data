"""Portable local Docker orchestration; works from PowerShell or a Unix shell."""
import argparse
from pathlib import Path
import subprocess
import sys

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root))
from taxi.common import month_date
p=argparse.ArgumentParser()
p.add_argument('--month',default='2025-01')
p.add_argument('--require-complete-quarter',action='store_true')
a=p.parse_args()
month_date(a.month)
def run(*args):
    subprocess.run(args,cwd=root,check=True)
run(sys.executable,str(root/'scripts/setup.py'))
run('docker','compose','up','-d','--wait','db')
run('docker','compose','--profile','pipeline','build')
for stage in ['ingest','transform','export']:
    extra=['--require-complete-quarter'] if stage=='export' and a.require_complete_quarter else []
    run('docker','compose','run','--rm','--no-deps',stage,stage,'--month',a.month,*extra)
run('docker','compose','run','--rm','--no-deps','test','selfcheck')
print('Completed. Read outputs/latest.json to find the immutable output snapshot.')
