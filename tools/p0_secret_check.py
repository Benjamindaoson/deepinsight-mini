"""Scan staged bytes for actual workspace credentials without displaying them."""
import json
import os
import subprocess

from app.config import config
from app.providers import ProviderVault


def main():
    values = {item['key'] for item in ProviderVault(config().data).read('workspace')['profiles']}
    values.update(os.getenv(name, '') for name in ('MINI_API_KEY','LLM_API_KEY','OPENAI_API_KEY'))
    needles = [value.encode() for value in values if len(value)>7]
    names = subprocess.check_output(['git','diff','--cached','--name-only','-z']).split(b'\0')
    findings=[]
    for name in filter(None,names):
        path=name.decode('utf-8')
        body=subprocess.check_output(['git','show',':'+path])
        if any(needle in body for needle in needles):
            findings.append(path)
    print(json.dumps({'checked_files':sum(bool(x) for x in names),'secret_matches':len(findings),'paths':findings}))
    if findings:
        raise SystemExit('Do not commit: a credential matched staged content.')


if __name__=='__main__':
    main()
