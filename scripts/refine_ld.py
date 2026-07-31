#!/usr/bin/env python3
"""Refine longDescription + fields for specific tools via Qwen. Reads /tmp/daily_keys.json."""
import re, json, requests, sys

KEYS = json.load(open('/tmp/daily_keys.json'))
QWEN_KEY = KEYS['QWEN_API_KEY_1']

QWEN_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
PROXIES = {"http": "http://127.0.0.1:7890", "https": "http://127.0.0.1:7890"}
TOOLS_FILE = "src/data/tools.ts"

def call_qwen(prompt):
    resp = requests.post(
        QWEN_URL,
        headers={"Authorization": f"Bearer {QWEN_KEY}", "Content-Type": "application/json"},
        json={"model": "qwen-plus", "messages": [
            {"role": "system", "content": "You are a B2B SaaS tool review expert. Output ONLY valid JSON. No markdown, no code fences, no trailing commas."},
            {"role": "user", "content": prompt}
        ], "max_tokens": 6000, "temperature": 0.7},
        proxies=PROXIES, timeout=180
    )
    resp.raise_for_status()
    result = resp.json()['choices'][0]['message']['content']
    result = re.sub(r'^```(?:json)?\s*|\s*```$', '', result.strip(), flags=re.MULTILINE)
    # fix invalid JSON escapes
    result = re.sub(r'\\([^\\"/bfnrtu])', r'\1', result)
    result = re.sub(r',\s*}', '}', result)
    result = re.sub(r',\s*]', ']', result)
    # replace smart quotes
    result = result.replace('\u2018', "'").replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
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
                    end = bpos + j + 1
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

def format_list(items):
    return "[\n      " + ",\n      ".join([f"'{esc(x)}'" for x in items]) + ",\n    ],"

def refine_one(content, tid, tname, tcategory, current_ld):
    entry_start, entry_end, entry = find_entry(content, tid)
    if not entry:
        print(f"  EXIT_NOTFOUND {tid}"); return content

    prompt = f"""You are improving a detailed tool review entry for "{tname}" (category: {tcategory}).

IMPORTANT CONTEXT - this is the CURRENT (inadequate) longDescription:
"{current_ld}"

Generate a COMPLETELY REWRITTEN, much richer review. Return ONLY valid JSON with these keys:
1. "longDescription": A comprehensive G2-style review of 300-500 words. Cover: what the tool does, core features, ideal target users, key strengths, notable limitations, how it compares to main competitors, and who it is best/worst suited for. Be specific and concrete (mention real capabilities). ASCII quotes only.
2. "pros": 6 specific advantages
3. "cons": 3-4 disadvantages
4. "features": 10-12 concrete features
5. "pricing": short string
6. "pricingDetail": 2-3 sentence pricing breakdown
7. "useCase": 2-3 sentence use case
8. "scoreBreakdown": {{"features": N, "reviews": N, "momentum": N, "popularity": N}} with N between 3.5 and 5.0
9. "userQuotes": 2-3 realistic customer quotes as [{{"role":"","company":"","quote":""}}]

RULES: ASCII quotes only. Specific, actionable, factual items. Reference real features of {tname}. Output ONLY the valid JSON object."""

    try:
        data = call_qwen(prompt)
        print(f"  OK Qwen {tid}: ld_chars={len(data.get('longDescription',''))} pros={len(data.get('pros',[]))} cons={len(data.get('cons',[]))} feat={len(data.get('features',[]))}")
    except Exception as e:
        print(f"  ERR Qwen {tid}: {e}")
        return content

    new_entry = entry

    # longDescription - single quoted multi-line
    r = find_field(new_entry, 'longDescription')
    if r:
        new_ld_esc = esc(data.get('longDescription', current_ld))
        new_val = "longDescription:\n      '" + new_ld_esc + "',"
        new_entry = new_entry[:r[0]] + new_val + new_entry[r[1]:]

    # arrays
    for fname, key in [('pros','pros'), ('cons','cons'), ('features','features')]:
        r = find_array_field(new_entry, fname)
        if r:
            new_val = f"{fname}: " + format_list(data.get(key, []))
            new_entry = new_entry[:r[0]] + new_val + new_entry[r[1]:]

    # string fields
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
        uq_entries.append("      {\n"
            f"        role: '{esc(uq.get('role', 'User'))}',\n"
            f"        company: '{esc(uq.get('company', 'Company'))}',\n"
            f"        quote: '{esc(uq.get('quote', 'Good tool.'))}',\n"
            "      }")
    new_uq = "userQuotes: [\n" + ",\n".join(uq_entries) + ",\n    ],"
    r = find_array_field(new_entry, 'userQuotes')
    if r: new_entry = new_entry[:r[0]] + new_uq + new_entry[r[1]:]

    new_entry = re.sub(r"\]\n(\s+)([a-z])", r"],\n\1\2", new_entry)

    # Verify
    if new_entry.count('{') != new_entry.count('}'):
        print(f"  ERR brace: {new_entry.count('{')}/{new_entry.count('}')}"); return content
    missing = [f for f in ['longDescription:', 'pros:', 'cons:', 'features:', 'pricing:', 'pricingDetail:', 'useCase:', 'scoreBreakdown:', 'userQuotes:'] if f not in new_entry]
    if missing:
        print(f"  ERR missing: {missing}"); return content

    new_content = content[:entry_start] + new_entry + content[entry_end:]
    if new_content.count('{') != new_content.count('}'):
        print("  ERR file brace imbalance!"); return content
    new_content = new_content.replace(',,', ',')
    print(f"  DONE refined: {tname}")
    return new_content

if __name__ == '__main__':
    import os
    os.chdir('/home/edi/ai-tools-astro')
    ts = [
        {'id': 'clockwise', 'name': 'Clockwise', 'category': 'AI Calendar Management'},
        {'id': 'coze', 'name': 'Coze (ByteDance)', 'category': 'AI Agent & Framework'},
        {'id': 'dify', 'name': 'Dify', 'category': 'AI Agent & Framework'},
    ]
    content = open(TOOLS_FILE).read()
    for ti in ts:
        print("=" * 60)
        print(f"Refining: {ti['name']} ({ti['id']})")
        # extract current longDescription for context
        idx = content.find(f"id: '{ti['id']}'")
        seg = content[idx:idx+2000]
        ld_m = re.search(r"longDescription:\s*\n\s*'((?:[^'\\]|\\.)*?)'", seg, re.DOTALL)
        cur_ld = ld_m.group(1) if ld_m else ""
        content = refine_one(content, ti['id'], ti['name'], ti['category'], cur_ld)
        if not content:
            print("  ABORT"); sys.exit(1)
    with open(TOOLS_FILE, 'w') as f:
        f.write(content)
    print("\n=== All refined ===")
