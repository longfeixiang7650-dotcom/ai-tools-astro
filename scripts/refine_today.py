#!/usr/bin/env python3
"""Refine 3 shortest unrefined tools via Qwen (daily task Priority B)."""
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from refine_ld import refine_one

TOOLS_FILE = "src/data/tools.ts"

ts = [
    {'id': 'canva-ai', 'name': 'Canva AI', 'category': 'AI Image & Design'},
    {'id': 'writesonic', 'name': 'Writesonic', 'category': 'AI Writing & Content'},
    {'id': 'heygen', 'name': 'HeyGen', 'category': 'AI Video & Audio'},
]

os.chdir('/home/edi/ai-tools-astro')
content = open(TOOLS_FILE).read()

for ti in ts:
    print("=" * 60)
    print(f"Refining: {ti['name']} ({ti['id']})")
    idx = content.find(f"id: '{ti['id']}'")
    if idx < 0:
        print(f"  NOTFOUND {ti['id']}")
        continue
    seg = content[idx:idx+2000]
    ld_m = re.search(r"longDescription:\s*\n?\s*'((?:[^'\\]|\\.)*?)'", seg, re.DOTALL)
    cur_ld = ld_m.group(1) if ld_m else ""
    new_content = refine_one(content, ti['id'], ti['name'], ti['category'], cur_ld)
    if not new_content:
        print("  ABORT"); sys.exit(1)
    content = new_content

with open(TOOLS_FILE, 'w') as f:
    f.write(content)
print("\n=== All 3 refined & written ===")
