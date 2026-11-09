"""Host-scheduled entry point; three-month lag gives the source time to be published."""
import datetime as dt
from pathlib import Path
import subprocess
import sys

today=dt.date.today()
# Run on the 15th; publication is typically delayed by two months.
# A three-month offset avoids asking for the month that might still be unpublished.
index=today.year*12+today.month-1-3
year,month0=divmod(index,12)
month=f'{year:04d}-{month0+1:02d}'
script=Path(__file__).with_name('run_pipeline.py')
subprocess.run([sys.executable,str(script),'--month',month],check=True)
