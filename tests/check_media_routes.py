"""Check media rule parsing with real Traefik. Run: python3 tests/check_media_routes.py (requires Docker)."""

import json
import pathlib
import re
import subprocess
import tempfile
import time
import urllib.request

root = pathlib.Path(__file__).resolve().parents[1]
routers = {}
for source in ('staging/core-service/docker-compose.yml', 'prod/docker-compose.yml'):
    for name, rule in re.findall(r'traefik\.http\.routers\.(acs-media[^.]+)\.rule=(.+)"', (root / source).read_text()):
        rule = rule.replace('${STAGING_HOST:?STAGING_HOST must be set}', 'acs-staging.narutchai.com')
        rule = rule.replace('${RUSTFS_BUCKET:-acs-media}', 'acs-bucket-staging')
        routers[name] = {'rule': rule, 'entryPoints': ['web'], 'service': 'probe'}

assert set(routers) == {'acs-media-staging-http', 'acs-media-staging-https', 'acs-media-prod'}

config = {'http': {'routers': routers, 'services': {'probe': {'loadBalancer': {'servers': [{'url': 'http://127.0.0.1:9'}]}}}}}
scratch = tempfile.TemporaryDirectory(prefix='acs-media-route-test-')
config_path = pathlib.Path(scratch.name) / 'dynamic.yml'
config_path.write_text(json.dumps(config))
container = subprocess.check_output([
    'docker', 'run', '-d', '--rm', '-p', '127.0.0.1::8080',
    '-v', f'{config_path}:/etc/traefik/dynamic.yml:ro', 'traefik:v3.7.13',
    '--providers.file.filename=/etc/traefik/dynamic.yml',
    '--entrypoints.web.address=:8000', '--api.insecure=true',
], text=True).strip()
try:
    port = subprocess.check_output(['docker', 'port', container, '8080/tcp'], text=True).strip().split(':')[-1]
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/rawdata', timeout=1) as response:
                data = json.load(response)
            if all(name + '@file' in data.get('routers', {}) for name in routers):
                break
        except (OSError, ValueError):
            pass
        time.sleep(0.1)
    else:
        raise RuntimeError('Traefik did not load all media routers')
    failures = []
    for name in routers:
        result = data['routers'][name + '@file']
        print(name + ': ' + result['status'])
        for error in result.get('error', []):
            print(error)
        if result['status'] != 'enabled':
            failures.append(name)
    assert not failures, 'Media router parsing failed: ' + ', '.join(failures)
finally:
    subprocess.run(['docker', 'rm', '-f', container], check=True, stdout=subprocess.DEVNULL)
    scratch.cleanup()
