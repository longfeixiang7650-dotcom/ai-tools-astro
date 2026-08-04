#!/usr/bin/env python3
"""Daily Priority B: refine 3 shortest unrefined tools via Qwen (2026-08-04 batch)."""
import re, sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from refine_ld import refine_one

TOOLS_FILE = "src/data/tools.ts"

ts = [
    {'id': 'sudowrite', 'name': 'Sudowrite', 'category': 'AI Writing & Content'},
    {'id': 'contentbot', 'name': 'ContentBot', 'category': 'AI Writing & Content'},
    {'id': 'seek-ai', 'name': 'Seek AI', 'category': 'AI Data & Analytics'},
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
    seg = content[idx:idx+2500]
    ld_m = re.search(r"longDescription:\s*\n?\s*'((?:[^'\\]|\\.)*?)'", seg, re.DOTALL)
    cur_ld = ld_m.group(1) if ld_m else ""
    new_content = refine_one(content, ti['id'], ti['name'], ti['category'], cur_ld)
    if not new_content:
        print("  ABORT"); sys.exit(1)
    content = new_content

with open(TOOLS_FILE, 'w') as f:
    f.write(content)
print("\n=== All 3 refined & written ===")
