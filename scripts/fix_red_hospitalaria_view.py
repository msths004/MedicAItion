"""
fix_red_hospitalaria_view.py — Corrige la visibilidad y dependencias de la Red Hospitalaria
"""

import os

CSS_PATH = os.path.abspath("frontend/style.css")
LINUX_CSS = os.path.abspath("Linux_Ver/frontend/style.css")
JS_PATH = os.path.abspath("frontend/app.js")
LINUX_JS = os.path.abspath("Linux_Ver/frontend/app.js")

# 1. FIX CSS: Permitir display block !important a panel-red-hospitalaria-section
def fix_css(path):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    # Block 1
    target1 = "body.mode-legal #panel-legal-section {\n  display: block !important;\n}"
    rule1 = "body.mode-red-hospitalaria #panel-red-hospitalaria-section {\n  display: block !important;\n}"
    
    if rule1 not in content and target1 in content:
        content = content.replace(target1, target1 + "\n\n" + rule1, 1)
        print(f"Regla CSS 1 inyectada en {os.path.basename(path)}")

    # Block 2 (Viewport strict isolation)
    target2 = "body.mode-legal #panel-legal-section {\n  display: block !important;\n}"
    # find second occurrence
    idx = content.find(target2)
    if idx != -1:
        idx2 = content.find(target2, idx + len(target2))
        if idx2 != -1:
            content = content[:idx2 + len(target2)] + "\n\n" + rule1 + content[idx2 + len(target2):]
            print(f"Regla CSS 2 inyectada en {os.path.basename(path)}")

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

fix_css(CSS_PATH)
fix_css(LINUX_CSS)

# 2. FIX JS: Definir escapeHtml en app.js
ESCAPE_HTML_FN = """
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
"""

def fix_js(path):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    if "function escapeHtml(str)" not in content:
        # Insert before RED HOSPITALARIA & INTERCONSULTA FEDERADA
        anchor = "// RED HOSPITALARIA & INTERCONSULTA FEDERADA"
        if anchor in content:
            content = content.replace(anchor, ESCAPE_HTML_FN + "\n" + anchor, 1)
            print(f"escapeHtml inyectado en {os.path.basename(path)}")
        else:
            content += "\n" + ESCAPE_HTML_FN
            print(f"escapeHtml appended en {os.path.basename(path)}")

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

fix_js(JS_PATH)
fix_js(LINUX_JS)

print("Fixes aplicados correctamente.")
