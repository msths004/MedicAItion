# -*- coding: utf-8 -*-
"""
remove_copilot_panel.py
Removes the invasive Dr. Oso / Pulso right panel from #consulta-layout
leaving ONLY the floating draggable Dr. Oso icon and floating chat drawer.
Updates both Windows and Linux_Ver codebases.
"""
import os
import re

ROOT_DIRS = [
    r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion",
    r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion\Linux_Ver"
]

for base in ROOT_DIRS:
    idx_path = os.path.join(base, "frontend", "index.html")
    if not os.path.exists(idx_path):
        continue

    with open(idx_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Locate and remove <aside class="clinical-split-panel panel-ai-copilot" ... </aside>
    pattern = r'<!-- =========================================================\s+COLUMNA 3: COPILOTO IA LOCAL.*?<aside class="clinical-split-panel panel-ai-copilot".*?<\/aside>'
    cleaned = re.sub(pattern, '<!-- Columna 3 eliminada: Dr. Oso opera exclusivamente desde el icono flotante accesible -->', html, flags=re.DOTALL)
    
    if cleaned != html:
        with open(idx_path, "w", encoding="utf-8") as f:
            f.write(cleaned)
        print(f"Successfully removed panel-ai-copilot from {idx_path}")
    else:
        # Fallback search for just <aside ... id="panel-ai-copilot"> ... </aside>
        pattern2 = r'<aside class="clinical-split-panel panel-ai-copilot" id="panel-ai-copilot".*?<\/aside>'
        cleaned2 = re.sub(pattern2, '<!-- Dr. Oso opera exclusivamente desde el icono flotante -->', html, flags=re.DOTALL)
        if cleaned2 != html:
            with open(idx_path, "w", encoding="utf-8") as f:
                f.write(cleaned2)
            print(f"Successfully removed panel-ai-copilot (fallback pattern) from {idx_path}")
        else:
            print(f"Warning: pattern not matched in {idx_path}")

print("Done updating index.html files.")
