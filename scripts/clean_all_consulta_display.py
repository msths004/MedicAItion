# -*- coding: utf-8 -*-
"""
scripts/clean_all_consulta_display.py
=====================================
Ensures #consulta-layout NEVER has 'display: grid' unless scoped to body.mode-consulta.
"""

import os
import re

ROOTS = [
    r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion",
    r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion\Linux_Ver"
]

def clean_css(base_dir):
    p = os.path.join(base_dir, "frontend", "style.css")
    if not os.path.exists(p):
        return
    with open(p, "r", encoding="utf-8") as f:
        css = f.read()

    # Replace standalone '#consulta-layout {\n  display: grid;' or '#consulta-layout {\n  display: grid !important;'
    # with a comment or remove display property
    def repl(m):
        full = m.group(0)
        # If preceded by body.mode-consulta, keep it
        start = m.start()
        prefix = css[max(0, start - 30):start]
        if 'body.mode-consulta' in prefix:
            return full
        # Otherwise remove 'display: grid;' or 'display: grid !important;'
        cleaned = re.sub(r'display:\s*grid\s*(!important)?\s*;', '/* display managed by mode-consulta */', full)
        return cleaned

    # Match any #consulta-layout { ... }
    new_css = re.sub(r'(?:body\.mode-consulta\s+)?#consulta-layout\s*\{[^}]+\}', repl, css)

    # Ensure the strict isolation block is present at the bottom
    isolation_block = """
/* ==========================================================================
   VIEWPORT TAB SYSTEM: AISLAMIENTO ESTRICTO DE PESTAÑAS (ZERO BLEED)
   ========================================================================== */
.view-viewport > .view-panel {
  display: none !important;
}

body.mode-dashboard #panel-dashboard-section {
  display: block !important;
}

body.mode-consulta #consulta-layout {
  display: grid !important;
}

body.mode-expedientes #panel-patients-section {
  display: flex !important;
}

body.mode-expediente #panel-expediente-section {
  display: block !important;
}

body.mode-agenda #panel-agenda-section {
  display: block !important;
}

body.mode-reportes #panel-reports-section {
  display: block !important;
}

body.mode-herramientas #panel-herramientas-section {
  display: block !important;
}

body.mode-config #panel-config-section {
  display: block !important;
}

body.mode-legal #panel-legal-section {
  display: block !important;
}
"""
    # Remove existing isolation blocks and append clean one
    new_css = re.sub(
        r'/\*\s*={5,}\s*VIEWPORT TAB SYSTEM: AISLAMIENTO ESTRICTO DE PESTAÑAS[\s\S]*?body\.mode-legal\s+#panel-legal-section\s*\{\s*display:\s*block\s*!important;\s*\}',
        '',
        new_css
    )
    new_css = new_css.strip() + "\n\n" + isolation_block.strip() + "\n"

    with open(p, "w", encoding="utf-8") as f:
        f.write(new_css)
    print(f"Cleaned all consulta display rules in: {p}")

for root in ROOTS:
    clean_css(root)
print("Done!")
