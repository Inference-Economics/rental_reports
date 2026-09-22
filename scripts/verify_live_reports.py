"""Do not announce a report until both deployed pages match their source HTML."""
import argparse
import hashlib
from pathlib import Path
import time
from urllib.request import Request, urlopen
from urllib.error import URLError

parser = argparse.ArgumentParser()
parser.add_argument('--month', required=True)
args = parser.parse_args()
pending = {city: hashlib.sha256(Path(f'reports/{city}/{args.month}/index.html').read_bytes()).hexdigest() for city in ('toronto','vancouver')}
for attempt in range(40):
    for city, expected in list(pending.items()):
        url = f'https://reports.inference-economics.com/reports/{city}/{args.month}/?verify={int(time.time())}'
        try:
            with urlopen(Request(url, headers={'Cache-Control':'no-cache'}), timeout=20) as response:
                actual = hashlib.sha256(response.read()).hexdigest()
            if actual == expected:
                del pending[city]
                print(f'{city}: deployed HTML verified', flush=True)
        except URLError:
            pass
    if not pending:
        break
    time.sleep(15)
else:
    raise SystemExit('Pages deployment did not serve the expected HTML for: ' + ', '.join(pending))
