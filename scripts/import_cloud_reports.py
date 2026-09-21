"""Validate the completed cloud bundle before touching published report paths."""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import zipfile


def import_bundle(archive, month, root):
    if not re.fullmatch(r'\d{4}-\d{2}', month):
        raise ValueError('Month must be YYYY-MM')
    date.fromisoformat(month + '-01')
    expected = {'toronto/index.html', 'vancouver/index.html'}
    with zipfile.ZipFile(archive) as z:
        if set(z.namelist()) != expected | {'manifest.json'} or len(z.namelist()) != 3:
            raise ValueError('Unexpected bundle contents')
        if any(i.file_size > 30_000_000 for i in z.infolist()):
            raise ValueError('Oversized bundle entry')
        manifest = json.loads(z.read('manifest.json'))
        if manifest['month'] != month or set(manifest['sha256']) != expected:
            raise ValueError('Bundle month/schema mismatch')
        payloads = {name: z.read(name) for name in expected}
        for name, data in payloads.items():
            if hashlib.sha256(data).hexdigest() != manifest['sha256'][name]:
                raise ValueError('HTML checksum mismatch')
            if '<html' not in data.decode('utf-8').lower():
                raise ValueError('Invalid HTML')
    for name, data in payloads.items():
        city = name.split('/')[0]
        target = root / 'reports' / city / month / 'index.html'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    print(f'Validated both reports for {month}')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--archive', type=Path, required=True)
    p.add_argument('--month', required=True)
    p.add_argument('--root', type=Path, default=Path('.'))
    args = p.parse_args()
    import_bundle(args.archive, args.month, args.root)
