"""Check staged Git content without printing secrets. Run before a public push."""
import re
import subprocess
from pathlib import Path
import sys

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
secrets = []
env_file = root / '.env'
if env_file.exists():
    env = dict(line.split('=', 1) for line in env_file.read_text().splitlines() if '=' in line and not line.startswith('#'))
    secrets.extend(value for key, value in env.items() if key in ('CLONE_MASTER_KEY', 'CLONE_ADMIN_PASSWORD') and value)
    if env.get('CLONE_MASTER_KEY') and (root / 'data/clone.sqlite3').exists():
        from app.store import Store
        connections = Store(root / 'data', env['CLONE_MASTER_KEY']).get('connections') or {}
        secrets.extend(config['token'] for config in connections.values() if config.get('token'))
        profiles = Store(root / 'data', env['CLONE_MASTER_KEY']).get('server-profiles') or {}
        secrets.extend(p['connection']['token'] for p in profiles.get('profiles', []) if p['connection'].get('token'))
errors = []
for path in filter(None, paths):
    if path == 'ssh/.gitkeep':
        assert not subprocess.check_output(['git', 'show', ':' + path], cwd=root)
        continue
    lower = path.lower()
    if (lower.startswith(('data/', 'ssh/', '.venv/')) or lower == '.env' or
        (lower.startswith('.env.') and lower != '.env.example') or
        lower.endswith(('.pem', '.key', '.sqlite3', '.ccb', '.log')) or
        lower in ('files md/struttura.md', 'files md/todolist.md', 'files md/installazione.md')):
        errors.append(path + ': file locale riservato')
        continue
    content = subprocess.check_output(['git', 'show', ':' + path], cwd=root)
    text = content.decode('utf-8', errors='replace')
    if any(value.encode() in content for value in secrets):
        errors.append(path + ': credenziale locale rilevata')
    if re.search(r'-----BEGIN (?:OPENSSH |RSA |EC )?PRIVATE KEY-----\r?\n[A-Za-z0-9+/=]{40}', text):
        errors.append(path + ': chiave privata rilevata')
    if re.search(r'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b', text):
        errors.append(path + ': token GitHub rilevato')
if errors:
    print('\n'.join(errors))
    raise SystemExit(1)
print(f'Controllati {len(list(filter(None, paths)))} file: nessun dato locale o segreto noto rilevato.')
