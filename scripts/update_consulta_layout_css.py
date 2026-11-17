# -*- coding: utf-8 -*-
"""
update_consulta_layout_css.py
Updates #consulta-layout to a sleek 2-column layout and hides any residue of #panel-ai-copilot.
"""
import os
import re

ROOT_DIRS = [
    r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion",
    r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion\Linux_Ver"
]

two_column_rules = """
/* ==========================================================================
   NUEVA CONSULTA - REFINED 2-COLUMN WORKSTATION (DR. OSO SOLO FLOTANTE)
   ========================================================================== */
#panel-ai-copilot {
  display: none !important;
}

#consulta-layout {
  grid-template-columns: 360px minmax(0, 1fr) !important;
  gap: 24px !important;
  max-width: 1720px !important;
  width: 100% !important;
  margin: 0 auto !important;
}

@media (max-width: 1120px) {
  #consulta-layout {
    grid-template-columns: 1fr !important;
    gap: 18px !important;
  }
}
"""

for base in ROOT_DIRS:
    css_path = os.path.join(base, "frontend", "style.css")
    if not os.path.exists(css_path):
        continue

    with open(css_path, "r", encoding="utf-8") as f:
        css = f.read()

    # Replace old 3-column definitions
    css = re.sub(
        r'#consulta-layout\s*\{\s*grid-template-columns:\s*310px\s+minmax\(0,\s*1fr\)\s+340px\s*!important;',
        '#consulta-layout {\n  grid-template-columns: 360px minmax(0, 1fr) !important;',
        css
    )

    # Append refined 2-column rules at the end
    if "NUEVA CONSULTA - REFINED 2-COLUMN WORKSTATION" in css:
        idx = css.find("/* ==========================================================================\n   NUEVA CONSULTA - REFINED 2-COLUMN WORKSTATION")
        css = css[:idx] + two_column_rules
    else:
        css += "\n" + two_column_rules

    with open(css_path, "w", encoding="utf-8") as f:
        f.write(css)

    print(f"Updated 2-column rules in {css_path}")

print("Finished updating CSS.")
