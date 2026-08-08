#!/usr/bin/env python3
"""Daily cron Priority B: refine the remaining 2 unrefined tools (empty userQuotes).
Rewrites ONLY longDescription + userQuotes via refine_longdesc_uq (preserves 0-100 scoreBreakdown)."""
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from refine_today_ld_uq import refine_longdesc_uq

TOOLS_FILE = "src/data/tools.ts"
ts = [
    {'id': 'make-ai', 'name': 'Make AI', 'category': 'AI Visual Automation'},
    {'id': 'bubble-ai', 'name': 'Bubble AI', 'category': 'AI No-Code App Builder'},
]
os.chdir('/home/edi/ai-tools-astro')
content = open(TOOLS_FILE).read()
for ti in ts:
    print("=" * 60)
    print(f"Refining: {ti['name']} ({ti['id']})")
    idx = content.find(f"id: '{ti['id']}'")
    if idx < 0:
        print(f"  EXIT_NOTFOUND {ti['id']}"); sys.exit(1)
    seg = content[idx:idx+2500]
    ld_m = re.search(r"longDescription:\s*\n\s*'((?:[^'\\]|\\.)*?)'", seg, re.DOTALL)
    cur_ld = ld_m.group(1) if ld_m else ""
    new_content = refine_longdesc_uq(content, ti['id'], ti['name'], ti['category'], cur_ld)
    if not new_content:
        print("  ABORT"); sys.exit(1)
    content = new_content
with open(TOOLS_FILE, 'w') as f:
    f.write(content)
print("\n=== All refined ===")
