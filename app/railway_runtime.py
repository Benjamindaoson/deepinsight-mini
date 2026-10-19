"""One Railway service: supervised web and independent scheduler, shared volume."""
import hashlib
import json
import os
import shutil
import signal
import sqlite3
import subprocess
import sys
import time
from contextlib import closing
from pathlib import Path

from app.config import ROOT, config


def initialize_seed(seed_root, persistent_root):
    seed, target = Path(seed_root), Path(persistent_root)
    data, output = target/'data', target/'output'
    data.mkdir(parents=True, exist_ok=True)
    (output/'reports').mkdir(parents=True, exist_ok=True)
    database = data/'market.sqlite3'
    if database.exists() or not (seed/'market.sqlite3').exists():
        return
    for relative, destination in [('raw', data/'raw'), ('reports', output/'reports')]:
        if (seed/relative).exists():
            shutil.copytree(seed/relative, destination, dirs_exist_ok=True)
    temporary = database.with_suffix('.initializing')
    with closing(sqlite3.connect(seed/'market.sqlite3')) as source, closing(sqlite3.connect(temporary)) as sink:
        source.backup(sink)
    os.replace(temporary, database)
    (data/'seed-initialized.json').write_text(json.dumps({'source_sha256':hashlib.sha256((seed/'market.sqlite3').read_bytes()).hexdigest(),'at':time.time()}))


def initialize_workspace(store):
    from app.providers import ProviderVault, PROVIDERS, capabilities
    c = config()
    vault = ProviderVault(store.path.parent)
    existing = vault.read('workspace')['profiles']
    if existing or not c.key:
        return
    provider = next((name for name, item in PROVIDERS.items() if item['base_url'] == c.base_url), None)
    if not provider:
        raise ValueError('Configure an approved workspace model endpoint.')
    profile = vault.save('workspace', {'provider':provider,'label':'Workspace '+PROVIDERS[provider]['label'],'api_key':c.key})
    vault.update('workspace',profile['id'],models=[{'id':c.model,**capabilities(c.model)}])
    vault.select('workspace',profile['id'],c.model,os.getenv('MINI_THINKING','auto'))
    store.audit('WORKSPACE_MODEL_INITIALIZED',profile['id'],{'provider':provider,'model':c.model,'catalog':'Configured operator model; refresh explicitly for provider catalog.'})


def resource_metrics():
    from app.config import config
    rss = 0
    if os.name == 'posix' and Path('/proc/self/statm').exists():
        rss = int(Path('/proc/self/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')
    cgroup = Path('/sys/fs/cgroup/memory.current')
    limit = Path('/sys/fs/cgroup/memory.max')
    def number(path):
        try:
            return int(path.read_text().strip())
        except (ValueError,OSError):
            return None
    root = config().data.parent
    used = sum(p.stat().st_size for p in root.rglob('*') if p.is_file()) if root.exists() else 0
    disk = shutil.disk_usage(root)
    return {'process_rss_bytes':rss,'container_memory_bytes':number(cgroup),'container_memory_limit_bytes':number(limit),
            'persistent_file_bytes':used,'volume_disk_used_bytes':disk.used,'volume_disk_total_bytes':disk.total}


def main():
    persistent = Path(os.getenv('MINI_PERSIST_ROOT','/persist'))
    if os.getenv('MINI_REQUIRE_VOLUME') == '1':
        mount = os.getenv('RAILWAY_VOLUME_MOUNT_PATH')
        if not mount or Path(mount) != persistent or not persistent.is_dir():
            raise SystemExit('A persistent Railway volume must be mounted at the configured storage path.')
    if os.getenv('RAILWAY_ENVIRONMENT_ID') and not config().admin_token:
        raise SystemExit('Configure the application access token before public deployment.')
    os.environ.setdefault('MINI_DATA_DIR',str(persistent/'data'))
    os.environ.setdefault('MINI_OUTPUT_DIR',str(persistent/'output'))
    os.environ.setdefault('MINI_MAX_JOBS','1')
    os.environ.setdefault('MINI_TUNNEL_DNS','0')
    initialize_seed(ROOT/'deployment/seed',persistent)
    from app.database import Store
    store = Store()
    initialize_workspace(store)
    children = {}
    stopping = False
    def stop(*_):
        nonlocal stopping
        stopping = True
        for child in children.values():
            if child.poll() is None:
                child.terminate()
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    commands = {
        'web':[sys.executable,'-m','uvicorn','app.main:app','--host','0.0.0.0','--port',os.getenv('PORT','8080'),'--workers','1','--proxy-headers','--forwarded-allow-ips','*'],
        'scheduler':[sys.executable,'-m','app.monitoring.scheduler'],
    }
    for name, command in commands.items():
        children[name] = subprocess.Popen(command)
    try:
        while not stopping:
            for name, child in list(children.items()):
                if child.poll() is not None:
                    store.audit('PROCESS_RESTART',name,{'exit_code':child.returncode})
                    if name == 'web':
                        stop()
                        return 1
                    children[name] = subprocess.Popen(commands[name])
            time.sleep(1)
    finally:
        stop()
        for child in children.values():
            try:
                child.wait(timeout=20)
            except subprocess.TimeoutExpired:
                child.kill()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
