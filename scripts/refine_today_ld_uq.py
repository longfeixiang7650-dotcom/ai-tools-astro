#!/usr/bin/env python3
"""Minimal-risk refinement: rewrite ONLY longDescription + userQuotes for target tools.
Leaves scoreBreakdown / pros / cons / features / pricing / pricingDetail / useCase untouched
(so we don't reintroduce the 0-5 score scale). Reads /tmp/daily_keys.json."""
import re, json, requests, sys, os

os.chdir('/home/edi/ai-tools-astro')
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
        ], "max_tokens": 4000, "temperature": 0.7},
        proxies=PROXIES, timeout=180
    )
    resp.raise_for_status()
    result = resp.json()['choices'][0]['message']['content']
    result = re.sub(r'^```(?:json)?\s*|\s*```$', '', result.strip(), flags=re.MULTILINE)
    result = re.sub(r'\\([^\\"/bfnrtu])', r'\1', result)
    result = re.sub(r',\s*}', '}', result)
    result = re.sub(r',\s*]', ']', result)
    result = result.replace('\u2018', "'").replace('\u2019', "'").replace('\u201c', '"').replace('\u201d', '"')
    return json.loads(result)

def esc(s):
    s = s.replace('\\', '\\\\').replace("'", "\\'").replace('\n', ' ').replace('\r', '')
    return s

def find_entry(content, tool_id):
    idx = content.find(f"id: '{tool_id}'")
    if idx < 0: return None, None
    before = content[max(0, idx-300):idx]
    bp = before.rfind('{')
    if bp < 0: return None, None
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
    return entry_start, entry_start + i + 1

def find_field_span(text, fname):
    """Find range of a single-quoted string field value (including trailing comma)."""
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

def refine_longdesc_uq(content, tid, tname, tcategory, current_ld):
    entry_start, entry_end = find_entry(content, tid)
    if entry_start is None:
        print(f"  EXIT_NOTFOUND {tid}"); return content
    entry = content[entry_start:entry_end]

    prompt = f"""Improve the review entry for "{tname}" (category: {tcategory}).

CURRENT longDescription (inadequate, to be REPLACED):
\"\"\"
{current_ld}
\"\"\"

Generate a COMPLETELY REWRITTEN richer G2-style review. Return ONLY valid JSON with exactly these 2 keys:
1. "longDescription": A comprehensive 300-500 word (aim ~2000-2100 chars, 5-7 paragraphs) review. Cover: what the tool does, core features, ideal target users, key strengths, notable limitations, how it compares to main competitors, and who it is best/worst for. Be specific and concrete (mention real capabilities of {tname}). ASCII quotes only (no smart quotes).
2. "userQuotes": 3 realistic customer quotes as [{{"role":"","company":"","quote":""}}].

RULES: ASCII quotes only. Output ONLY the valid JSON object with no other text."""

    try:
        data = call_qwen(prompt)
        print(f"  OK Qwen {tid}: ld_chars={len(data.get('longDescription',''))} uq={len(data.get('userQuotes',[]))}")
    except Exception as e:
        print(f"  ERR Qwen {tid}: {e}")
        return content

    new_entry = entry

    # longDescription
    r = find_field_span(new_entry, 'longDescription')
    if r:
        ld = data.get('longDescription', current_ld)
        ld = esc(ld)
        # single-quoted multi-line format
        new_val = f"longDescription:\n      '{ld}',"
        new_entry = new_entry[:r[0]] + new_val + new_entry[r[1]:]
    else:
        print(f"  ERR no longDescription field {tid}"); return content

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
    if r:
        new_entry = new_entry[:r[0]] + new_uq + new_entry[r[1]:]
    else:
        print(f"  ERR no userQuotes field {tid}"); return content

    if new_entry.count('{') != new_entry.count('}'):
        print(f"  ERR brace: {new_entry.count('{')}/{new_entry.count('}')}"); return content

    new_content = content[:entry_start] + new_entry + content[entry_end:]
    if new_content.count('{') != new_content.count('}'):
        print("  ERR file brace imbalance!"); return content
    new_content = new_content.replace(',,', ',')
    print(f"  DONE refined: {tname}")
    return new_content

if __name__ == '__main__':
    # [id, name, category]
    ts = [
        ['picsart-ai', 'Picsart AI', 'AI Image & Design'],
        ['obviously-ai', 'Obviously AI', 'AI Data & Analytics'],
        ['krisp', 'Krisp', 'AI Audio Enhancement'],
    ]
    content = open(TOOLS_FILE).read()
    for tid, tname, tcategory in ts:
        print("=" * 60)
        print(f"Refining: {tname} ({tid})")
        idx = content.find(f"id: '{tid}'")
        seg = content[idx:idx+2500]
        ld_m = re.search(r"longDescription:\s*\n\s*'((?:[^'\\]|\\.)*?)'", seg, re.DOTALL)
        cur_ld = ld_m.group(1) if ld_m else ""
        content = refine_longdesc_uq(content, tid, tname, tcategory, cur_ld)
        if not content:
            print("  ABORT"); sys.exit(1)
    with open(TOOLS_FILE, 'w') as f:
        f.write(content)
    print("\n=== All refined ===")
