"""Run all tests in an isolated Docker test stack with an ephemeral database."""
from pathlib import Path
import subprocess
import sys
root=Path(__file__).resolve().parents[1]
base=['docker','compose','-f','compose.test.yaml']
def run(args):
    subprocess.run(args,cwd=root,check=True)
run([sys.executable,'scripts/setup.py'])
try:
    run(base+['up','-d','--wait','db'])
    run(base+['build','tests'])
    run(base+['run','--rm','--no-deps','tests'])
finally:
    # Only the separate ephemeral test stack is stopped; project data are retained.
    subprocess.run(base+['down'],cwd=root,check=False)
