#!/usr/bin/env python3
"""
Refine ai-tools-astro tools incrementally using Qwen API.
Safe field-by-field replacement using exact boundary detection.

Usage: python3 scripts/refine_tools.py [tool_id_1] [tool_id_2] [tool_id_3]
If no args given, defaults to: fireflies-ai, sisu, reclaim-ai
"""
import re, json, requests, sys

with open('/tmp/real_keys.json') as f:
    keys = json.load(f)
QWEN_KEY = keys['QWEN_API_KEY_1']

QWEN_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
PROXIES = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}
TOOLS_FILE = "src/data/tools.ts"

def call_qwen(prompt):
    resp = requests.post(
        QWEN_URL,
        headers={"Authorization": f"Bearer {QWEN_KEY}", "Content-Type": "application/json"},
        json={"model": "qwen-plus", "messages": [
            {"role": "system", "content": "You are a B2B SaaS tool review expert. Output ONLY valid JSON. No markdown, no code fences."},
            {"role": "user", "content": prompt}
        ], "max_tokens": 4096, "temperature": 0.7},
        proxies=PROXIES, timeout=120
    )
    resp.raise_for_status()
    result = resp.json()['choices'][0]['message']['content']
    result = re.sub(r'^```(?:json)?\s*|\s*```$', '', result.strip(), flags=re.MULTILINE)
    return json.loads(result)

def esc(s):
    s = s.replace('\\', '\\\\').replace("'", "\\'").replace('\n', ' ').replace('\r', '')
    return s

def find_entry(content, tool_id):
    idx = content.find(f"id: '{tool_id}'")
    if idx < 0: return None, None, None
    before = content[max(0, idx-300):idx]
    bp = before.rfind('{')
    if bp < 0: return None, None, None
    entry_start = max(0, idx-300) + bp
    text = content[entry_start:]
    depth = 0; in_str = False; sq = None; i = 0
    while i < len(text):
        ch = text[i]
        if in_str:
            if ch == '\\': i += 2; continue
            if ch == sq: in_str = False
        else:
            if ch in "'\"": in_str = True; sq = ch
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0: break
        i += 1
    return entry_start, entry_start + i + 1, text[:i+1]

def find_array_field(text, fname):
    """⚠️ CRITICAL: end = bpos + j + 1 (NOT fpos + 1 + j + 1)"""
    fpos = text.find(f"{fname}: [")
    if fpos < 0:
        fpos = text.find(f"{fname}:\n")
        if fpos < 0: return None
        fpos = text.find("[", fpos)
        if fpos < 0: return None
        fpos = fpos - 1
    bpos = text.find("[", fpos)
    if bpos < 0: return None
    rest = text[bpos:]
    bd = 0; in_str = False; sq = None; j = 0
    while j < len(rest):
        ch = rest[j]
        if in_str:
            if ch == '\\': j += 2; continue
            if ch == sq: in_str = False
        else:
            if ch in "'\"": in_str = True; sq = ch
            elif ch == '[': bd += 1
            elif ch == ']':
                bd -= 1
                if bd == 0:
                    end = bpos + j + 1  # 🔥 FIXED: was fpos+1+j+1 (off-by-12 error!)
                    if end < len(text) and text[end] == ',': end += 1
                    return (fpos, end)
        j += 1
    return None

def find_field(text, fname):
    fpos = text.find(f"{fname}:")
    if fpos < 0: return None
    qpos = text.find("'", fpos)
    if qpos < 0: return None
    i = qpos + 1
    while i < len(text):
        if text[i] == '\\' and i+1 < len(text): i += 2; continue
        if text[i] == "'":
            end = i + 1
            if end < len(text) and text[end] == ',': end += 1
            return (fpos, end)
        i += 1
    return None

def find_scoreBreakdown(text):
    fpos = text.find("scoreBreakdown:")
    if fpos < 0: return None
    rest = text[fpos:]
    depth = 0; in_str = False; sq = None; i = 0
    while i < len(rest):
        ch = rest[i]
        if in_str:
            if ch == '\\': i += 2; continue
            if ch == sq: in_str = False
        else:
            if ch in "'\"": in_str = True; sq = ch
            elif ch == '{': depth += 1
            elif ch == '}':
                depth -= 1
                if depth == 0:
                    end = fpos + i + 1
                    if end < len(text) and text[end] == ',': end += 1
                    return (fpos, end)
        i += 1
    return None

def refine_one(content, tid, tname, tcategory):
    entry_start, entry_end, entry = find_entry(content, tid)
    if not entry:
        print(f"  ❌ Entry not found for {tid}"); return content
    
    prompt = f"""Generate improved content for "{tname}" (category: {tcategory}).

Return ONLY valid JSON with:
1. "pros": 6-7 specific advantages
2. "cons": 3-4 disadvantages
3. "features": 10-12 features
4. "pricing": Short string
5. "pricingDetail": 2-3 sentence pricing
6. "useCase": 2-3 sentence use case
7. "scoreBreakdown": {{"features":N, "reviews":N, "momentum":N, "popularity":N}} (3.5-5.0)
8. "userQuotes": [{{"role":"","company":"","quote":""}}] (2-3 items)

RULES: ASCII quotes only. Specific, actionable items. Output ONLY valid JSON."""
    
    try:
        data = call_qwen(prompt)
        print(f"  ✅ Qwen: pros={len(data.get('pros',[]))} cons={len(data.get('cons',[]))} features={len(data.get('features',[]))}")
    except Exception as e:
        print(f"  ❌ Qwen error: {e}"); return content
    
    new_entry = entry
    
    # Field-by-field replacement
    fields = [
        ('pros', 'pros: [\n      ' + ',\n      '.join([f"'{esc(p)}'" for p in data.get('pros', [])]) + ',\n    ],'),
        ('cons', 'cons: [\n      ' + ',\n      '.join([f"'{esc(c)}'" for c in data.get('cons', [])]) + ',\n    ],'),
        ('features', 'features: [\n      ' + ',\n      '.join([f"'{esc(f)}'" for f in data.get('features', [])]) + ',\n    ],'),
    ]
    for fname, new_val in fields:
        r = find_array_field(new_entry, fname)
        if r: new_entry = new_entry[:r[0]] + new_val + new_entry[r[1]:]
    
    # String fields
    sf = [
        ('pricing', f"pricing: '{esc(data.get('pricing', ''))}',"),
        ('pricingDetail', f"pricingDetail:\n      '{esc(data.get('pricingDetail', ''))}',"),
        ('useCase', f"useCase: '{esc(data.get('useCase', ''))}',"),
    ]
    for fname, new_val in sf:
        r = find_field(new_entry, fname)
        if r: new_entry = new_entry[:r[0]] + new_val + new_entry[r[1]:]
    
    # scoreBreakdown
    r = find_scoreBreakdown(new_entry)
    if r:
        sb = data.get('scoreBreakdown', {})
        new_sb = (f"scoreBreakdown: {{\n"
                  f"      features: {sb.get('features', 4.5)},\n"
                  f"      reviews: {sb.get('reviews', 4.3)},\n"
                  f"      momentum: {sb.get('momentum', 4.4)},\n"
                  f"      popularity: {sb.get('popularity', 4.2)},\n"
                  f"    }},")
        new_entry = new_entry[:r[0]] + new_sb + new_entry[r[1]:]
    
    # userQuotes
    uq_entries = []
    for uq in data.get('userQuotes', []):
        uq_entries.append(f"      {{\n"
            f"        role: '{esc(uq.get('role', 'User'))}',\n"
            f"        company: '{esc(uq.get('company', 'Company'))}',\n"
            f"        quote: '{esc(uq.get('quote', 'Good tool.'))}',\n"
            f"      }}")
    new_uq = "userQuotes: [\n" + ",\n".join(uq_entries) + ",\n    ],"
    r = find_array_field(new_entry, 'userQuotes')
    if r: new_entry = new_entry[:r[0]] + new_uq + new_entry[r[1]:]
    
    # Fix trailing commas
    new_entry = re.sub(r"\]\n(\s+)([a-z])", r"],\n\1\2", new_entry)
    
    # Verify
    if new_entry.count('{') != new_entry.count('}'):
        print(f"  ❌ Brace imbalance: {new_entry.count('{')}/{new_entry.count('}')}"); return content
    missing = [f for f in ['pros:', 'cons:', 'features:', 'pricing:', 'pricingDetail:', 'useCase:', 'scoreBreakdown:', 'userQuotes:'] if f not in new_entry]
    if missing:
        print(f"  ❌ Missing: {missing}"); return content
    
    new_content = content[:entry_start] + new_entry + content[entry_end:]
    if new_content.count('{') != new_content.count('}'):
        print(f"  ❌ File brace imbalance!"); return content
    new_content = new_content.replace(',,', ',')
    print(f"  ✅ {tname} refined")
    return new_content

if __name__ == '__main__':
    default_tools = [
        {'id': 'fireflies-ai', 'name': 'Fireflies.ai', 'category': 'AI Meeting Intelligence'},
        {'id': 'sisu', 'name': 'Sisu', 'category': 'AI Data & Analytics'},
        {'id': 'reclaim-ai', 'name': 'Reclaim AI', 'category': 'AI Productivity'},
    ]
    
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)) + '/..')
    
    content = open('src/data/tools.ts').read()
    
    if len(sys.argv) > 1:
        # Build tools list from args (format: id:name:category)
        from_tools = []
        for arg in sys.argv[1:4]:
            parts = arg.split(':')
            if len(parts) >= 2:
                from_tools.append({'id': parts[0], 'name': parts[1], 'category': parts[2] if len(parts) > 2 else 'General'})
        tools = from_tools if from_tools else default_tools
    else:
        tools = default_tools
    
    for ti in tools:
        print(f"{'='*60}\nRefining: {ti['name']} ({ti['id']})")
        content = refine_one(content, ti['id'], ti['name'], ti['category'])
        if not content:
            print("  ABORTING"); sys.exit(1)
    
    with open('src/data/tools.ts', 'w') as f: f.write(content)
    print(f"\n{'='*60}\n✅ All tools refined!")
