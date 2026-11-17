# -*- coding: utf-8 -*-
"""
scripts/fix_tabs_isolation.py
=============================
Solves tab view leaking and isolation:
1. Replaces invalid nested <main id="panel-consulta-col2"> with <div id="panel-consulta-col2"> in index.html.
2. Removes legacy mode-expedientes and mode-consulta rules that selectively hid/showed panels.
3. Removes 'display: grid !important' directly on #consulta-layout so it only displays when in 'mode-consulta'.
4. Implements strict .view-viewport > .view-panel display isolation in style.css.
5. Refactors switchMainTab in app.js to guarantee clean tab transitions.
6. Synchronizes changes to Linux_Ver.
"""

import os
import re

ROOTS = [
    r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion",
    r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion\Linux_Ver"
]

def fix_index_html(base_dir):
    p = os.path.join(base_dir, "frontend", "index.html")
    if not os.path.exists(p):
        return
    with open(p, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace <main class="clinical-split-panel panel-consulta-col2" with <div
    old_tag = '<main class="clinical-split-panel panel-consulta-col2" id="panel-consulta-col2">'
    new_tag = '<div class="clinical-split-panel panel-consulta-col2" id="panel-consulta-col2">'
    if old_tag in content:
        content = content.replace(old_tag, new_tag)
        # Find the matching closing tag right before Columna 3
        target = '</main>\n\n          <!-- =========================================================\n               COLUMNA 3:'
        if target in content:
            content = content.replace(target, '</div>\n\n          <!-- =========================================================\n               COLUMNA 3:')
        else:
            # Fallback regex
            content = re.sub(
                r'</main>(\s*<!--\s*={5,}\s*COLUMNA 3)',
                r'</div>\1',
                content
            )
        print(f"Fixed nested <main> in: {p}")

    with open(p, "w", encoding="utf-8") as f:
        f.write(content)


def fix_style_css(base_dir):
    p = os.path.join(base_dir, "frontend", "style.css")
    if not os.path.exists(p):
        return
    with open(p, "r", encoding="utf-8") as f:
        css = f.read()

    # 1. Remove legacy mode rules:
    legacy_pattern = re.compile(
        r'/\*\s*Grid Layout control based on active mode\s*\*/[\s\S]*?body\.mode-expedientes\s+\.panel-results\s*\{\s*display:\s*none\s*!important;\s*\}',
        re.MULTILINE
    )
    if legacy_pattern.search(css):
        css = legacy_pattern.sub('/* Legacy mode rules removed for strict viewport isolation */', css)
        print(f"Removed legacy mode rules in: {p}")

    # 2. In #consulta-layout, remove 'display: grid !important;' so it only displays when in mode-consulta
    css = re.sub(
        r'(#consulta-layout\s*\{\s*)display:\s*grid\s*!important;',
        r'\1/* display handled by body.mode-consulta */',
        css
    )

    # 3. Add or update the strict viewport isolation system
    isolation_block = """
/* ==========================================================================
   VIEWPORT TAB SYSTEM: AISLAMIENTO ESTRICTO DE PESTAÑAS (ZERO BLEED)
   Cada sección .view-panel dentro de .view-viewport SOLO es visible cuando
   corresponde a la pestaña activa (body.mode-*).
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

    if "VIEWPORT TAB SYSTEM: AISLAMIENTO ESTRICTO DE PESTAÑAS" in css:
        css = re.sub(
            r'/\*\s*={5,}\s*VIEWPORT TAB SYSTEM: AISLAMIENTO ESTRICTO DE PESTAÑAS[\s\S]*?body\.mode-legal\s+#panel-legal-section\s*\{\s*display:\s*block\s*!important;\s*\}',
            isolation_block.strip(),
            css
        )
    else:
        css = css + "\n\n" + isolation_block

    with open(p, "w", encoding="utf-8") as f:
        f.write(css)
    print(f"Updated style.css with strict isolation in: {p}")


def fix_app_js(base_dir):
    p = os.path.join(base_dir, "frontend", "app.js")
    if not os.path.exists(p):
        return
    with open(p, "r", encoding="utf-8") as f:
        content = f.read()

    new_switch_func = """function switchMainTab(tab) {
  AppState.mainTab = tab;

  const btnDash = document.getElementById('nav-btn-dashboard');
  const btnCons = document.getElementById('nav-btn-consulta');
  const btnExpe = document.getElementById('nav-btn-expedientes');
  const btnClinExp = document.getElementById('nav-btn-clinica-exp');
  const btnAgnd = document.getElementById('nav-btn-agenda');
  const btnRep  = document.getElementById('nav-btn-reportes');
  const btnIa   = document.getElementById('nav-btn-ia-tools');
  const btnCfg  = document.getElementById('nav-btn-config');
  const btnLegal = document.getElementById('nav-btn-legal');

  if (btnDash) btnDash.classList.toggle('active', tab === 'dashboard');
  if (btnCons) btnCons.classList.toggle('active', tab === 'consulta');
  if (btnExpe) btnExpe.classList.toggle('active', tab === 'expedientes');
  if (btnClinExp) btnClinExp.classList.toggle('active', tab === 'expediente');
  if (btnAgnd) btnAgnd.classList.toggle('active', tab === 'agenda');
  if (btnRep)  btnRep.classList.toggle('active', tab === 'reportes');
  if (btnIa)   btnIa.classList.toggle('active', tab === 'herramientas');
  if (btnCfg)  btnCfg.classList.toggle('active', tab === 'config');
  if (btnLegal) btnLegal.classList.toggle('active', tab === 'legal');

  // Actualizar modo en el body para CSS
  document.body.className = `mode-${tab}`;

  // Diccionario de paneles de vista con inicializadores seguros
  const viewPanels = {
    'dashboard': { id: 'panel-dashboard-section', display: 'block', init: () => typeof refreshDashboard === 'function' && refreshDashboard() },
    'consulta': { id: 'consulta-layout', display: 'grid', init: () => {} },
    'expedientes': { id: 'panel-patients-section', display: 'flex', init: () => typeof loadPatients === 'function' && loadPatients() },
    'expediente': { id: 'panel-expediente-section', display: 'block', init: () => typeof initSpecializedCareView === 'function' && initSpecializedCareView() },
    'agenda': { id: 'panel-agenda-section', display: 'block', init: () => typeof renderCalendar === 'function' && renderCalendar() },
    'reportes': { id: 'panel-reports-section', display: 'block', init: () => typeof renderReportsView === 'function' && renderReportsView() },
    'herramientas': { id: 'panel-herramientas-section', display: 'block', init: () => typeof initHerramientasView === 'function' && initHerramientasView() },
    'config': { id: 'panel-config-section', display: 'block', init: () => typeof loadSecurityConfigView === 'function' && loadSecurityConfigView() },
    'legal': { id: 'panel-legal-section', display: 'block', init: () => typeof loadLegalView === 'function' && loadLegalView() }
  };

  // Ocultar estrictamente todas las vistas excepto la activa
  Object.keys(viewPanels).forEach(key => {
    const item = viewPanels[key];
    const el = document.getElementById(item.id);
    if (el) {
      if (key === tab) {
        el.style.display = item.display;
        try {
          item.init();
        } catch (err) {
          console.warn(`[Nav] Error al inicializar vista ${key}:`, err);
        }
      } else {
        el.style.display = 'none';
      }
    }
  });

  const titleEl = document.getElementById('results-panel-title');
  const descEl  = document.getElementById('results-panel-desc');
  if (tab === 'consulta') {
    if (titleEl) titleEl.textContent = 'Previsualización de Notas';
    if (descEl)  descEl.textContent  = 'Sincronización en tiempo real con motor CIE-10';
  }
}"""

    # Replace old switchMainTab
    old_start = content.find('function switchMainTab(tab) {')
    if old_start != -1:
        next_fn = content.find('function setMode', old_start)
        if next_fn == -1:
            next_fn = content.find('/* ── MODE TOGGLE', old_start)
        end_brace = content.rfind('}', old_start, next_fn)
        if end_brace != -1:
            content = content[:old_start] + new_switch_func + content[end_brace + 1:]
            print(f"Replaced switchMainTab in: {p}")

    with open(p, "w", encoding="utf-8") as f:
        f.write(content)


for root in ROOTS:
    print(f"\nProcessing root: {root}")
    fix_index_html(root)
    fix_style_css(root)
    fix_app_js(root)

print("\nAll files successfully updated!")
