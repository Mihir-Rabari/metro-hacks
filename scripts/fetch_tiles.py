#!/usr/bin/env python3
"""Download offline map tiles (CARTO dark theme) for the Ahmedabad-Gandhinagar metro corridor.

Bbox covers all Yellow + Red line stations + buffer. Tiles are vendored into
kit/vendor/leaflet/tiles/ and served by a custom Leaflet TileLayer pointing at
relative paths, so the map works with airplane mode ON.
"""
import math
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

# Corridor bbox (lat_min, lon_min, lat_max, lon_max) with buffer
BBOX = (22.97, 72.50, 23.28, 72.72)
ZOOMS = [11, 12, 13, 14]
OUT = os.path.join(os.path.dirname(__file__), '..', 'kit', 'vendor', 'leaflet', 'tiles')
UA = {'User-Agent': 'metro-hacks/2026 offline-map-vendor (educational hackathon; one-time bulk fetch)'}
URLS = [
    'https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
    'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
]

def deg2num(lat, lon, z):
    lat_rad = math.radians(lat)
    n = 2.0 ** z
    x = int((lon + 180.0) / 360.0 * n)
    y = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return max(0, min(int(n) - 1, x)), max(0, min(int(n) - 1, y))

def tile_range(z):
    x0, y0 = deg2num(BBOX[0], BBOX[1], z)
    x1, y1 = deg2num(BBOX[2], BBOX[3], z)
    # Mercator y decreases northward — sort so the range is never empty
    return x0, max(x0, x1), min(y0, y1), max(y0, y1)

def fetch_tile(z, x, y, tries=3):
    path = os.path.join(OUT, str(z), str(x), f'{y}.png')
    if os.path.exists(path) and os.path.getsize(path) > 100:
        return 'skip'
    for attempt in range(tries):
        url = URLS[attempt % len(URLS)].format(z=z, x=x, y=y)
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=20) as r:
                data = r.read()
            if len(data) < 100:
                raise IOError(f'tiny tile {len(data)}')
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'wb') as f:
                f.write(data)
            return 'ok'
        except Exception:
            time.sleep(0.5 * (attempt + 1))
    return 'fail'

def main():
    jobs = []
    for z in ZOOMS:
        x0, x1, y0, y1 = tile_range(z)
        for x in range(x0, x1 + 1):
            for y in range(y0, y1 + 1):
                jobs.append((z, x, y))
    print(f'{len(jobs)} tiles to fetch across zooms {ZOOMS}')
    ok = fail = 0
    with ThreadPoolExecutor(max_workers=6) as ex:
        for result in ex.map(lambda j: fetch_tile(*j), jobs):
            if result == 'fail':
                fail += 1
            else:
                ok += 1
    total = 0
    for root, _, files in os.walk(OUT):
        total += sum(os.path.getsize(os.path.join(root, f)) for f in files)
    print(f'DONE ok={ok} fail={fail} total_size={total/1e6:.1f}MB')
    if fail:
        sys.exit(1)

if __name__ == '__main__':
    main()
