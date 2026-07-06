#!/usr/bin/env python3
"""
嘉兴红色实践 · 日间动线地图自动生成工具
======================================
基于高德静态地图 API + PIL 叠加手绘路线及标注
一日一图，自动标注关键点位并画动线

依赖: requests, Pillow
用法: python3 scripts/gen-itinerary-maps.py [--regen]
"""

import requests, sys, math, os
from PIL import Image, ImageDraw, ImageFont

# ---- Configuration ----
API_KEY = '20bf843285acba4d6902b0872ca7f940'
BASE_URL = "https://restapi.amap.com/v3/staticmap"
IMG_W, IMG_H = 600, 450
OUT_DIR = os.path.dirname(os.path.abspath(__file__))   # scripts/
PROJECT_DIR = os.path.dirname(OUT_DIR)                 # 嘉兴实践/
MAP_DIR = os.path.join(PROJECT_DIR, 'maps') if os.path.basename(PROJECT_DIR) == '嘉兴实践' else os.path.join(os.path.expanduser('~'), 'python-learning', '嘉兴实践', 'maps')

# Coordinate table
COORDS = {
    'hotel':    (120.761707, 30.763524),
    'new_hall': (120.7618, 30.7477),
    'red_boat': (120.7590, 30.7455),
    'hero_park':(120.7580, 30.7465),
    'old_hall': (120.7600, 30.7480),
    'shen_jr':  (120.7625, 30.7490),
    'cemetery': (120.7550, 30.7420),
    'interview':(120.7605, 30.7500),
    'nanhu_area':(120.7595, 30.7485),
    'tuanwei':  (120.7640, 30.7550),
    'station':  (120.7660, 30.7700),
}
COLORS = ['#FF6600', '#FF0000', '#0000FF', '#00AA00', '#880088', '#0088CC']
LAT_SCALE = 111000
LNG_SCALE = 95300

# ---- Day Configs ----
DAYS = [
    {
        'name': 'day1',
        'title': 'Day 1 — 7/11 南湖核心',
        'center': (120.761, 30.755), 'zoom': 14,
        'points': [('酒店', 'hotel'), ('新馆', 'new_hall'), ('红船', 'red_boat'),
                   ('英雄园', 'hero_park'), ('老馆', 'old_hall'), ('沈钧儒', 'shen_jr')],
        'route': ['hotel', 'new_hall', 'red_boat', 'hero_park', 'old_hall', 'shen_jr'],
    },
    {
        'name': 'day2',
        'title': 'Day 2 — 7/12 口述史+烈士陵园',
        'center': (120.759, 30.751), 'zoom': 14,
        'points': [('酒店', 'hotel'), ('采访点', 'interview'), ('烈士陵园', 'cemetery')],
        'route': ['hotel', 'interview', 'cemetery'],
    },
    {
        'name': 'day3',
        'title': 'Day 3 — 7/13 补拍+问卷',
        'center': (120.760, 30.753), 'zoom': 14,
        'points': [('酒店', 'hotel'), ('南湖周边', 'nanhu_area')],
        'route': ['hotel', 'nanhu_area'],
    },
    {
        'name': 'day4',
        'title': 'Day 4 — 7/14 盖章+收尾',
        'center': (120.761, 30.755), 'zoom': 14,
        'points': [('酒店', 'hotel'), ('纪念馆', 'new_hall'), ('团市委', 'tuanwei')],
        'route': ['hotel', 'tuanwei', 'new_hall'],
    },
    {
        'name': 'day5',
        'title': 'Day 5 — 7/15 打卡+返程',
        'center': (120.763, 30.766), 'zoom': 14,
        'points': [('酒店', 'hotel'), ('嘉兴站', 'station')],
        'route': ['hotel', 'station'],
    },
]

def lnglat_to_pixel(lng, lat, cx, cy, zoom):
    mpp = {10: 152, 11: 76, 12: 38, 13: 19, 14: 9.5, 15: 4.8}.get(zoom, 9.5)
    px = IMG_W / 2 + (lng - cx) * LNG_SCALE / mpp
    py = IMG_H / 2 - (lat - cy) * LAT_SCALE / mpp
    return int(px), int(py)

def fetch_base_map(center, zoom):
    """Download AMap static base map"""
    params = {'key': API_KEY, 'location': f'{center[0]},{center[1]}', 'zoom': zoom, 'size': f'{IMG_W}*{IMG_H}'}
    r = requests.get(BASE_URL, params=params, timeout=15)
    if r.headers.get('content-type', '').startswith('image'):
        return r.content
    else:
        raise RuntimeError(f'API error: {r.text[:200]}')

def draw_markers_and_route(base_bytes, day_cfg):
    """Overlay route line + labeled markers on base map"""
    from io import BytesIO
    img = Image.open(BytesIO(base_bytes)).convert('RGBA')
    overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    cx, cy = day_cfg['center']
    zoom = day_cfg['zoom']
    
    font_label = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 16)
    font_title = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 18)
    
    # Route line
    if day_cfg.get('route'):
        pix = [lnglat_to_pixel(COORDS[k][0], COORDS[k][1], cx, cy, zoom) for k in day_cfg['route']]
        for i in range(len(pix) - 1):
            draw.line([pix[i], pix[i+1]], fill=COLORS[i % 6], width=4)
            mx = (pix[i][0] + pix[i+1][0]) // 2
            my = (pix[i][1] + pix[i+1][1]) // 2
            ang = math.atan2(pix[i+1][1] - pix[i][1], pix[i+1][0] - pix[i][0])
            al = 10
            draw.polygon([(mx, my), (mx - al * math.cos(ang - 0.5), my - al * math.sin(ang - 0.5)),
                          (mx - al * math.cos(ang + 0.5), my - al * math.sin(ang + 0.5))],
                         fill=COLORS[i % 6])
    
    # Markers
    for i, (label, key) in enumerate(day_cfg['points']):
        lng, lat = COORDS[key]
        px, py = lnglat_to_pixel(lng, lat, cx, cy, zoom)
        r = 10
        color = COLORS[i % 6]
        draw.ellipse([(px - r, py - r), (px + r, py + r)], fill=color, outline='#FFFFFF', width=3)
        lx, ly = px + r + 5, py - 10
        bbox = font_label.getbbox(label)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        draw.rectangle([(lx - 2, ly - 2), (lx + tw + 4, ly + th + 2)], fill='#000000CC')
        draw.text((lx, ly), label, fill='#FFFFFF', font=font_label)
    
    # Title
    draw.text((10, 8), day_cfg['title'], fill='#000000', font=font_title)
    
    result = Image.alpha_composite(img, overlay).convert('RGB')
    return result


def generate_all(max_retries=3):
    os.makedirs(MAP_DIR, exist_ok=True)
    results = []
    for day in DAYS:
        out_path = os.path.join(MAP_DIR, f'{day["name"]}_map.jpg')
        print(f'→ {day["title"]} ...', end=' ')
        for attempt in range(max_retries):
            try:
                base = fetch_base_map(day['center'], day['zoom'])
                img = draw_markers_and_route(base, day)
                img.save(out_path, quality=90)
                sz = os.path.getsize(out_path) // 1024
                print(f'✅ {sz}KB')
                results.append((day['name'], out_path))
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    import time; time.sleep(10)
                    print(f'retry#{attempt+1}', end=' ')
                else:
                    print(f'❌ {e}')
        # Rate limit avoidance
        import time; time.sleep(3)
    
    print(f'\n✅ 共生成 {len(results)} 张地图 → {MAP_DIR}/')
    return results

if __name__ == '__main__':
    generate_all()
