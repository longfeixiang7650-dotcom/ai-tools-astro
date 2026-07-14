#!/usr/bin/env python3
"""Batch screenshot AI tool websites for aitoolsnav.net"""
import re, os, sys, time, json

SCREENSHOTS_DIR = "/home/edi/ai-tools-astro/public/images/screenshots"
TOOLS_FILE = "/home/edi/ai-tools-astro/src/data/tools.ts"
BATCH_SIZE = 5
PROXY = "http://127.0.0.1:7890"

os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

# Read tools
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

# Filter tools that already have screenshots
existing = set(os.listdir(SCREENSHOTS_DIR))
pending = [(tid, url) for tid, url in tools if f"{tid}.jpg" not in existing and f"{tid}.png" not in existing]

print(f"Total tools: {len(tools)}")
print(f"Already have screenshots: {len(tools) - len(pending)}")
print(f"Need screenshots: {len(pending)}")

if not pending:
    print("All done!")
    sys.exit(0)

# Take first BATCH_SIZE screenshots
to_process = pending[:BATCH_SIZE]

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
    )
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        proxy={"server": PROXY} if PROXY else None,
        locale="en-US",
        extra_http_headers={"Accept-Language": "en-US,en;q=0.9"}
    )
    
    success = 0
    fail = 0
    for tid, url in to_process:
        print(f"\n[{success+fail+1}/{len(pending)}] {tid}: {url}")
        page = None
        try:
            page = context.new_page()
            page.set_default_timeout(20000)
            resp = page.goto(url, wait_until="domcontentloaded", timeout=20000)
            status = resp.status if resp else "no response"
            
            # Wait a moment for hero image / main content to load
            page.wait_for_timeout(3000)
            
            # Take screenshot of first 800px height (hero section)
            filepath = os.path.join(SCREENSHOTS_DIR, f"{tid}.png")
            page.screenshot(path=filepath, full_page=False)
            
            # Verify file size
            fsize = os.path.getsize(filepath)
            if fsize > 2000:
                print(f"  ✅ {status} ({fsize/1024:.0f}KB)")
                success += 1
            else:
                print(f"  ⚠️  {status} but tiny file ({fsize}B)")
                fail += 1
                
        except Exception as e:
            print(f"  ❌ {str(e)[:80]}")
            fail += 1
        finally:
            if page:
                page.close()
        
        time.sleep(2)  # Delay between tools
    
    context.close()
    browser.close()

print(f"\nDone this batch: {success} success, {fail} fail")
print(f"Total screenshots now: {len(os.listdir(SCREENSHOTS_DIR))}")
