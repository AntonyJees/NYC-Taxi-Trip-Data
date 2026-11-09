"""Create local credentials without overwriting an existing environment."""
import os
from pathlib import Path
import secrets

root = Path(__file__).resolve().parents[1]
for name in ["data/raw","outputs"]:
    (root/name).mkdir(parents=True,exist_ok=True)
path = root/".env"
if not path.exists():
    values = {name:secrets.token_hex(24) for name in ["POSTGRES_PASSWORD","PIPELINE_PASSWORD","READER_PASSWORD"]}
    values.update(LOCAL_UID=str(os.getuid() if hasattr(os,"getuid") else 1000),LOCAL_GID=str(os.getgid() if hasattr(os,"getgid") else 1000))
    # Containers run as a non-root user, including when setup is called by root.
    if values['LOCAL_UID'] == '0':
        values.update(LOCAL_UID='10001',LOCAL_GID='10001')
        for name in ['data/raw','outputs']:
            os.chown(root/name,10001,10001)
    path.write_text("".join(f"{k}={v}\n" for k,v in values.items()))
    path.chmod(0o600)
    print("Created .env and local data directories. Keep .env private.")
else:
    print("Existing .env preserved.")
