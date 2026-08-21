#!/usr/bin/env python3
"""
网易云歌单抓取器（登录态版）
用法: COOKIE='MUSIC_U=xxx; NMTID=yyy' python3 netease_playlist_fetch.py <user_home_url>
依赖: playwright (chromium-1217 缓存)
"""
import os
import sys
import json
import time
from playwright.sync_api import sync_playwright

EXE = "/home/ubuntu/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome"
COOKIE = os.environ.get("COOKIE", "")


def make_context(browser):
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        viewport={"width": 1440, "height": 900},
    )
    if COOKIE:
        for pair in COOKIE.split(";"):
            pair = pair.strip()
            if not pair or "=" not in pair:
                continue
            k, v = pair.split("=", 1)
            ctx.add_cookies([{
                "name": k.strip(),
                "value": v.strip(),
                "domain": ".music.163.com",
                "path": "/",
            }])
    return ctx


def get_playlists(page, user_url):
    """打开用户主页，收集歌单列表"""
    page.goto(user_url, timeout=30000)
    time.sleep(3)
    # 尝试直接抓歌单链接
    links = page.eval_on_selector_all(
        "a[href*='/playlist?id=']",
        "els => els.map(e => ({href: e.href, text: e.innerText.trim()}))",
    )
    # 去重
    seen = set()
    result = []
    for l in links:
        if l["href"] not in seen:
            seen.add(l["href"])
            result.append(l)
    return result


def main():
    if len(sys.argv) < 2:
        print("用法: COOKIE='...' python3 netease_playlist_fetch.py <user_home_url>")
        sys.exit(1)
    user_url = sys.argv[1]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, executable_path=EXE)
        ctx = make_context(browser)
        page = ctx.new_page()
        try:
            playlists = get_playlists(page, user_url)
            print(json.dumps(playlists, ensure_ascii=False, indent=2))
            print(f"\n共找到 {len(playlists)} 个歌单链接")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
