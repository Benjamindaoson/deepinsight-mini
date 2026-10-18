import re
from pathlib import Path
from app.database import Store

s = Store()
for row in s.query("SELECT title,published_at,raw_path FROM documents WHERE source_id='savills_q2_2026'"):
    raw = Path(row["raw_path"]).read_text(encoding="utf-8", errors="replace")
    print(row["title"], "stored:", row["published_at"])
    for pattern in [r'.{0,80}datePublished.{0,140}', r'.{0,80}dateModified.{0,140}',
                    r'.{0,80}published_time.{0,140}', r'.{0,70}06 August 2026.{0,100}',
                    r'.{0,70}01 October 2026.{0,100}']:
        print(pattern, re.findall(pattern, raw, re.I)[:5])
