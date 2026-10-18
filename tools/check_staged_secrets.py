"""Check staged text for exact known environment credentials without printing any credential."""
import os
import subprocess
from pathlib import Path

root=Path(__file__).resolve().parents[1]
keys=[value for name,value in os.environ.items() if any(word in name.upper() for word in ('API_KEY','AUTH_TOKEN','SMTP_PASSWORD','TELEGRAM_TOKEN','ADMIN_TOKEN')) and len(value)>=12]
files=subprocess.check_output(['git','ls-files','--cached','-z'],cwd=root).decode('utf-8').split('\0')
hits=[]
for name in files:
    if not name:
        continue
    p=root/name
    if p.is_file() and p.stat().st_size<2_000_000:
        text=p.read_text(encoding='utf-8',errors='ignore')
        if any(key in text for key in keys):
            hits.append(name)
print({'staged_files_checked':len(files)-1,'credential_matches':len(hits),'files':hits})
raise SystemExit(1 if hits else 0)
