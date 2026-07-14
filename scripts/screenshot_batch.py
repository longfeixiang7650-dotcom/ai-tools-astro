#!/usr/bin/env python3
"""Batch screenshot AI tool websites - process all remaining tools"""
import re, os, sys, time, json

SCREENSHOTS_DIR = "/home/edi/ai-tools-astro/public/images/screenshots"
TOOLS_FILE = "/home/edi/ai-tools-astro/src/data/tools.ts"
BATCH_SIZE = 20
PROXY = "http://127.0.0.1:7890"

os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

with open(TOOLS_FILE) as f:
    content = f.read()

idx = content.find("export const ALL_TOOLS")
tools_section = content[idx:]
blocks = tools_section.split("  {")
tools = []
for block in blocks:
    id_m = re.search(r"id:\s*'([^']+)'", block)
    url_m = re.search(r"websiteUrl:\s*'([^']+)'", block)
    if id_m and url_m:
        tools.append((id_m.group(1), url_m.group(1)))

existing = set(os.listdir(SCREENSHOTS_DIR))
pending = [(tid, url) for tid, url in tools if f"{tid}.png" not in existing]
skipped = len(tools) - len(pending)

print(f"Total: {len(tools)} | Already have: {skipped} | Need: {len(pending)}")

if not pending:
    print("All screenshots exist!")
    sys.exit(0)

to_process = pending[:20]
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
    )
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
        proxy={"server": PROXY} if PROXY else None,
        locale="en-US"
    )

    success = 0
    fail = 0
    for tid, url in to_process:
        page = None
        try:
            page = context.new_page()
            page.set_default_timeout(15000)
            resp = page.goto(url, wait_until="domcontentloaded", timeout=15000)
            # Wait for visual content
            page.wait_for_timeout(3000)
            filepath = os.path.join(SCREENSHOTS_DIR, f"{tid}.png")
            page.screenshot(path=filepath, full_page=False)
            fsize = os.path.getsize(filepath)
            if fsize > 2000:
                print(f"  ✅ {tid} ({fsize/1024:.0f}KB)")
                success += 1
            else:
                print(f"  ⚠️  {tid} tiny ({fsize}B)")
                fail += 1
        except Exception as e:
            print(f"  ❌ {tid}: {str(e)[:60]}")
            fail += 1
        finally:
            if page: page.close()
        time.sleep(1.5)

    context.close()
    browser.close()

print(f"\n✅ Batch done: {success} success, {fail} fail")
total = len([f for f in os.listdir(SCREENSHOTS_DIR) if f.endswith('.png')])
print(f"Total screenshots: {total}/{len(tools)}")
