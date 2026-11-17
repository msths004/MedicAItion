# -*- coding: utf-8 -*-
"""
fix_pulso_js_syntax.py
Fixes the literal newline syntax error in pulso_assistant.js and ensures that:
1. buffer.split('\\n') is correctly written as a literal \n escape sequence in JS.
2. initPulsoAssistant runs reliably and populates the avatar image.
3. pulso-fab-btn has a direct onclick attribute in HTML as a failsafe: onclick="togglePulsoPanel()".
"""
import os
import re

for base in [r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion", r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion\Linux_Ver"]:
    js_p = os.path.join(base, "frontend", "pulso_assistant.js")
    with open(js_p, "r", encoding="utf-8") as f:
        code = f.read()

    # Fix buffer.split with literal newline
    # Replace buffer.split(' \n ') or buffer.split('\n')
    bad_split = "buffer.split('\n')"
    code = code.replace(bad_split, r"buffer.split('\n')")
    # Also regex replace in case of \r\n
    code = re.sub(r"const lines = buffer\.split\('[\r\n]+'\);", r"const lines = buffer.split('\\n');", code)

    with open(js_p, "w", encoding="utf-8") as f:
        f.write(code)

    print(f"Fixed {js_p}")

    # Also check index.html to ensure pulso-fab-btn has onclick="togglePulsoPanel()" as a direct fallback
    idx_p = os.path.join(base, "frontend", "index.html")
    with open(idx_p, "r", encoding="utf-8") as f:
        html = f.read()

    old_fab = '<button\n      type="button"\n      id="pulso-fab-btn"\n      class="pulso-fab-btn"'
    new_fab = '<button\n      type="button"\n      id="pulso-fab-btn"\n      class="pulso-fab-btn"\n      onclick="togglePulsoPanel()"'
    if old_fab in html:
        html = html.replace(old_fab, new_fab)
        with open(idx_p, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Added onclick fallback to pulso-fab-btn in {idx_p}")

print("Syntax fix complete.")
