#!/usr/bin/env python3
"""Bake a template into ONE self-contained HTML file (dist/).

Everything — CSS, vendored libs, kit JS, data JSON, model weights, and (for the
city template) the offline map tiles as base64 — is inlined. The result opens
from a double-click with airplane mode ON: no fetch(), no CORS, no server, no
network. This is the artifact you demo to judges.

Run:  python3 scripts/bake.py ops   -> dist/ops.html
      python3 scripts/bake.py city  -> dist/city.html
"""
import base64
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DATA_FILES = ['stations', 'timetable', 'fares', 'assets', 'faults-seed', 'lastmile', 'busroutes', 'crowding', 'replies', 'complaints-seed']

def read(path):
    with open(os.path.join(ROOT, path), encoding='utf-8') as f:
        return f.read()

def inline_assets(html, template):
    # ---- CSS ----
    html = re.sub(
        r'<link rel="stylesheet" href="\.\./\.\./kit/(dash\.css)">',
        lambda m: '<style>\n' + read(f'kit/{m.group(1)}') + '\n</style>',
        html)
    html = re.sub(
        r'<link rel="stylesheet" href="\.\./\.\./kit/vendor/(leaflet\.css)">',
        lambda m: '<style>\n' + read(f'kit/vendor/{m.group(1)}') + '\n</style>',
        html)

    # ---- data + models injected before the app script ----
    data_js = ['<script>\nwindow.__DATA__ = {']
    for name in DATA_FILES:
        obj = json.loads(read(f'data/{name}.json'))
        data_js.append(f'{json.dumps(name)}: {json.dumps(obj, ensure_ascii=False)},')
    data_js.append('};\n</script>')
    models_js = '<script>\nwindow.__MODELS__ = {\n' + \
        'triage: ' + read('models/triage.json') + ',\ncrowding: ' + read('models/crowding.json') + '\n};\n</script>'
    tiles_js = ''
    if template == 'city':
        tiles = {}
        tdir = os.path.join(ROOT, 'kit/vendor/leaflet/tiles')
        for z in os.listdir(tdir):
            for x in os.listdir(os.path.join(tdir, z)):
                for y in os.listdir(os.path.join(tdir, z, x)):
                    with open(os.path.join(tdir, z, x, y), 'rb') as f:
                        tiles[f'{z}/{x}/{y[:-4]}'] = 'data:image/png;base64,' + base64.b64encode(f.read()).decode()
        tiles_js = '<script>\nwindow.__TILES__ = ' + json.dumps(tiles) + ';\n</script>'
        print(f'  inlined {len(tiles)} map tiles as base64')

    # ---- vendor + kit scripts, in dependency order ----
    vendor = ['chart.umd.js'] if template in ('ops', 'ps07') else ['leaflet.js']
    kit = ['util.js', 'store.js', 'ai.js'] + (['map.js'] if template == 'city' else [])
    scripts = []
    for v in vendor:
        scripts.append('<script>\n' + read(f'kit/vendor/{v}') + '\n</script>')
    for k in kit:
        scripts.append('<script>\n' + read(f'kit/{k}') + '\n</script>')

    # strip the original script/link tags and inject ours
    html = re.sub(r'<script src="\.\./\.\./kit/vendor/[^"]+"></script>\n?', '', html)
    html = re.sub(r'<script src="\.\./\.\./kit/[^"]+"></script>\n?', '', html)
    head_inject = '\n'.join(scripts)
    html = html.replace('</head>', head_inject + '\n</head>')

    # inject data/models right before the inline app script
    html = html.replace('<script>\n/* DEV MODE', '<script>\n/* DEV MODE')
    m = re.search(r'<script>\s*\n?/\* DEV MODE', html)
    blob = '\n'.join(data_js) + '\n' + models_js + '\n' + tiles_js
    if m:
        html = html[:m.start()] + blob + '\n' + html[m.start():]
    else:
        html = html.replace('</body>', blob + '\n</body>')
    return html

def main():
    template = sys.argv[1] if len(sys.argv) > 1 else 'ops'
    src = read(f'templates/{template}/index.html')
    out = inline_assets(src, template)
    # sanity: no external refs may remain in MARKUP (vendored JS strings excluded)
    markup_only = re.sub(r'<script>.*?</script>|<style>.*?</style>', '', out, flags=re.S)
    leftovers = re.findall(r'(?:src|href)="(?!#|data:)(https?:|//)[^"]+"', markup_only)
    assert not leftovers, f'external refs remain: {leftovers}'
    fetches = re.findall(r'fetch\(\s*[\'"][^\'"]*https?://', out)
    assert not fetches, f'remote fetch() calls remain: {fetches}'
    os.makedirs(os.path.join(ROOT, 'dist'), exist_ok=True)
    # The PS-07 product bakes to dist/app.html — the artifact demoed to judges.
    fname = 'app.html' if template == 'ps07' else f'{template}.html'
    dest = os.path.join(ROOT, 'dist', fname)
    with open(dest, 'w', encoding='utf-8') as f:
        f.write(out)
    size = os.path.getsize(dest) / 1024
    print(f'BAKED dist/{fname}  ({size:.0f} KB)  external network refs: 0')

if __name__ == '__main__':
    main()
