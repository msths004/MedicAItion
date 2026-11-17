# -*- coding: utf-8 -*-
"""
scripts/rebuild_consulta_3col_layout.py
======================================
Reorganizes the Nueva Consulta module into the exact 3-column layout requested:
- Column 1: PACIENTES , DATOS DEL PACIENTE
- Column 2: MODULO DE CONSULTA
- Column 3:
    - Top: RESULTADOS (Previsualización de Notas NOM-004, Receta, Imprimir)
    - Bottom: SEGUIMIENTO DEL PACIENTE (Adherencia farmacológica, cómo se encuentra, síntomas de alerta)
"""

import os
import re

ROOTS = [
    r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion",
    r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion\Linux_Ver"
]

SEGUIMIENTO_HTML = """
            <!-- =========================================================
                 PANEL DERECHO INFERIOR: SEGUIMIENTO DEL PACIENTE
                 (Adherencia farmacológica, estado actual y síntomas de alerta)
                 ========================================================= -->
            <div class="panel panel-followup" id="panel-patient-followup">
              <div class="panel-header">
                <div class="panel-header-icon-title">
                  <div class="panel-badge-icon panel-badge-followup">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
                    </svg>
                  </div>
                  <div>
                    <h3 class="followup-panel-title">Seguimiento del Paciente</h3>
                    <p class="panel-desc">Adherencia a medicinas, bienestar y síntomas de alerta</p>
                  </div>
                </div>
                <span class="followup-live-status-pill" id="followup-adherence-pill">94% Adherencia</span>
              </div>

              <div class="followup-content-grid">
                
                <!-- 1. CÓMO TOMA SUS MEDICINAS (Adherencia Farmacológica) -->
                <div class="followup-card-block">
                  <div class="followup-block-header">
                    <span class="block-emoji">💊</span>
                    <strong>¿Cómo toma sus medicinas?</strong>
                  </div>
                  <div class="med-adherence-track">
                    <div class="adherence-bar-wrap">
                      <div class="adherence-bar-fill" id="adherence-bar-fill" style="width: 94%;"></div>
                    </div>
                    <div class="adherence-labels-row">
                      <span>Cumplimiento del tratamiento</span>
                      <strong id="adherence-pct-text">Excelente (94%)</strong>
                    </div>
                  </div>
                  <div class="med-schedule-checks" id="followup-meds-checks">
                    <label class="med-check-row">
                      <input type="checkbox" checked disabled />
                      <span>Dosis matutina tomada a tiempo (08:00 hrs)</span>
                      <span class="time-tag">✓ Tomada</span>
                    </label>
                    <label class="med-check-row">
                      <input type="checkbox" checked disabled />
                      <span>Dosis vespertina tomada (14:00 hrs)</span>
                      <span class="time-tag">✓ Tomada</span>
                    </label>
                    <label class="med-check-row pending">
                      <input type="checkbox" disabled />
                      <span>Dosis nocturna programada (21:00 hrs)</span>
                      <span class="time-tag pending">Próxima</span>
                    </label>
                  </div>
                </div>

                <!-- 2. CÓMO SE ENCUENTRA HOY (Bienestar y Estado Anímico) -->
                <div class="followup-card-block">
                  <div class="followup-block-header">
                    <span class="block-emoji">😊</span>
                    <strong>¿Cómo se encuentra hoy?</strong>
                  </div>
                  <div class="patient-mood-status-row">
                    <span class="mood-badge mood-good" id="followup-mood-badge">
                      🟢 Estable · Síntomas Leves Controlados
                    </span>
                  </div>
                  <p class="followup-report-text" id="followup-patient-report">
                    <em>"Paciente refiere mejoría clínica gradual en las últimas 48 horas sin mareos ni eventos adversos a la medicación."</em>
                  </p>
                </div>

                <!-- 3. SÍNTOMAS Y SIGNOS DE ALERTA (Telemonitoreo) -->
                <div class="followup-card-block alert-block">
                  <div class="followup-block-header">
                    <span class="block-emoji">🚨</span>
                    <strong>Síntomas & Signos de Alerta</strong>
                  </div>
                  <div class="alert-signals-row" id="followup-signals-row">
                    <div class="signal-badge ok">
                      <span class="signal-dot"></span>
                      <span>Sin datos de disnea</span>
                    </div>
                    <div class="signal-badge ok">
                      <span class="signal-dot"></span>
                      <span>Afebril (&lt; 37.0°C)</span>
                    </div>
                    <div class="signal-badge ok">
                      <span class="signal-dot"></span>
                      <span>Tensión en Rango</span>
                    </div>
                  </div>
                  <div class="triage-security-footer">
                    <span class="shield-mini">🛡️</span>
                    <span>Semáforo de Seguridad: <strong>VERDE (Riesgo Bajo)</strong></span>
                  </div>
                </div>

              </div>
            </div>
"""

def update_index_html(base_dir):
    p = os.path.join(base_dir, "frontend", "index.html")
    if not os.path.exists(p):
        return
    with open(p, "r", encoding="utf-8") as f:
        content = f.read()

    # Identificar la sección de consulta
    start_tag = '<section class="view-panel" id="consulta-layout" style="display:none">'
    end_tag = '</section>'
    
    start_idx = content.find(start_tag)
    if start_idx == -1:
        print(f"Could not find consulta-layout in {p}")
        return

    # Buscar el cierre de </section> para consulta-layout
    close_idx = content.find(end_tag, start_idx)
    consulta_section = content[start_idx:close_idx + len(end_tag)]

    # Verificar si ya tiene el panel de seguimiento
    if 'id="panel-patient-followup"' in consulta_section:
        print(f"Already updated 3-col layout in: {p}")
        return

    # Extraer panel-patient-vitals
    vitals_start = consulta_section.find('<aside class="clinical-split-panel panel-patient-vitals"')
    vitals_end = consulta_section.find('</aside>', vitals_start) + len('</aside>')
    col1_vitals = consulta_section[vitals_start:vitals_end]

    # Extraer panel-input
    input_start = consulta_section.find('<div class="panel panel-input">')
    input_end = consulta_section.find('<!-- RIGHT PANEL: Previsualización de Notas -->', input_start)
    if input_end == -1:
        input_end = consulta_section.find('<div class="panel panel-results"', input_start)
    # Retroceder al último </div> antes de RIGHT PANEL
    input_end_div = consulta_section.rfind('</div>', input_start, input_end) + len('</div>')
    col2_input = consulta_section[input_start:input_end_div]

    # Extraer panel-results
    results_start = consulta_section.find('<div class="panel panel-results"')
    # El final de panel-results es justo antes de </main>
    main_end = consulta_section.find('</main>', results_start)
    results_end = consulta_section.rfind('</div>', results_start, main_end) + len('</div>')
    col3_results = consulta_section[results_start:results_end]

    # Armar la nueva estructura limpia de 3 columnas
    new_consulta_section = f"""<section class="view-panel" id="consulta-layout" style="display:none">

          <!-- =========================================================
               COLUMNA 1: PACIENTES , DATOS DEL PACIENTE
               ========================================================= -->
          {col1_vitals.strip()}

          <!-- =========================================================
               COLUMNA 2: MODULO DE CONSULTA (ENTRADA Y CAPTURA)
               ========================================================= -->
          <main class="clinical-split-panel panel-consulta-col2" id="panel-consulta-col2">
            {col2_input.strip()}
          </main>

          <!-- =========================================================
               COLUMNA 3: RESULTADOS (ARRIBA) + SEGUIMIENTO DEL PACIENTE (ABAJO)
               ========================================================= -->
          <aside class="clinical-split-panel panel-consulta-col3" id="panel-consulta-col3">
            
            <!-- 3.1 RESULTADOS (Previsualización de Notas NOM-004, Receta, Imprimir) -->
            {col3_results.strip()}

            <!-- 3.2 SEGUIMIENTO DEL PACIENTE -->
            {SEGUIMIENTO_HTML.strip()}

          </aside>

        </section>"""

    content = content[:start_idx] + new_consulta_section + content[close_idx + len(end_tag):]
    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Successfully restructured consulta-layout into 3-column architecture in: {p}")


THREE_COLUMN_CSS = """
/* ==========================================================================
   NUEVA CONSULTA: ARQUITECTURA DE 3 COLUMNAS MODULAR
   - Columna 1: PACIENTES , DATOS DEL PACIENTE
   - Columna 2: MODULO DE CONSULTA
   - Columna 3 (Vertical Stack): RESULTADOS (Arriba) + SEGUIMIENTO PACIENTE (Abajo)
   ========================================================================== */

#consulta-layout {
  display: grid !important;
  grid-template-columns: 310px minmax(360px, 1fr) minmax(420px, 1.25fr) !important;
  gap: 22px !important;
  align-items: stretch !important;
  width: 100% !important;
  max-width: 1920px !important;
  margin: 0 auto !important;
  box-sizing: border-box !important;
}

@media (max-width: 1360px) {
  #consulta-layout {
    grid-template-columns: 290px minmax(340px, 1fr) minmax(380px, 1fr) !important;
    gap: 16px !important;
  }
}

@media (max-width: 1120px) {
  #consulta-layout {
    grid-template-columns: 1fr !important;
  }
}

/* Columna 1: Ficha del Paciente y Signos Basales */
.panel-patient-vitals {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 20px !important;
  padding: 20px !important;
  box-shadow: var(--shadow-friendly) !important;
  height: fit-content !important;
}

/* Columna 2: Módulo de Consulta (Entrada de Caso) */
.panel-consulta-col2 {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 20px !important;
  padding: 20px !important;
  box-shadow: var(--shadow-friendly) !important;
  display: flex !important;
  flex-direction: column !important;
}

.panel-consulta-col2 .panel-input {
  background: transparent !important;
  border: none !important;
  padding: 0 !important;
  box-shadow: none !important;
}

/* Columna 3: Contenedor Apilado Verticalmente */
.panel-consulta-col3 {
  display: flex !important;
  flex-direction: column !important;
  gap: 20px !important;
  background: transparent !important;
  border: none !important;
  box-shadow: none !important;
  padding: 0 !important;
}

/* 3.1 Bloque Superior: Resultados */
.panel-consulta-col3 .panel-results {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 20px !important;
  padding: 20px !important;
  box-shadow: var(--shadow-friendly) !important;
  min-height: 480px !important;
}

/* 3.2 Bloque Inferior: Seguimiento del Paciente */
.panel-followup {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 20px !important;
  padding: 20px !important;
  box-shadow: var(--shadow-friendly) !important;
  display: flex !important;
  flex-direction: column !important;
  gap: 14px !important;
}

.panel-badge-followup {
  background: var(--celeste-soft) !important;
  color: var(--celeste-primary) !important;
  border-radius: 50% !important;
  width: 36px !important;
  height: 36px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
}

.followup-panel-title {
  font-size: 16px !important;
  font-weight: 700 !important;
  color: var(--text-primary) !important;
  margin: 0 !important;
}

.followup-live-status-pill {
  background: #ecfdf5 !important;
  color: #059669 !important;
  border: 1px solid #a7f3d0 !important;
  font-size: 11.5px !important;
  font-weight: 700 !important;
  padding: 3px 10px !important;
  border-radius: 999px !important;
}

.followup-content-grid {
  display: flex !important;
  flex-direction: column !important;
  gap: 12px !important;
}

.followup-card-block {
  background: var(--bg-input) !important;
  border: 1px solid var(--border) !important;
  border-radius: 14px !important;
  padding: 12px 14px !important;
}

.followup-card-block.alert-block {
  background: #f0fdf4 !important;
  border-color: #bbf7d0 !important;
}

[data-theme="dark"] .followup-card-block.alert-block {
  background: #064e3b22 !important;
  border-color: #065f46 !important;
}

.followup-block-header {
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
  font-size: 13px !important;
  color: var(--text-primary) !important;
  margin-bottom: 8px !important;
}

.block-emoji {
  font-size: 15px !important;
}

/* Adherencia a Medicinas */
.adherence-bar-wrap {
  width: 100% !important;
  height: 8px !important;
  background: #e2eaf2 !important;
  border-radius: 999px !important;
  overflow: hidden !important;
  margin-bottom: 6px !important;
}

.adherence-bar-fill {
  height: 100% !important;
  background: linear-gradient(90deg, #10b981 0%, #34d399 100%) !important;
  border-radius: 999px !important;
}

.adherence-labels-row {
  display: flex !important;
  justify-content: space-between !important;
  font-size: 11.5px !important;
  color: var(--text-muted) !important;
  margin-bottom: 8px !important;
}

.adherence-labels-row strong {
  color: #059669 !important;
  font-weight: 700 !important;
}

.med-schedule-checks {
  display: flex !important;
  flex-direction: column !important;
  gap: 6px !important;
  border-top: 1px dashed var(--border) !important;
  padding-top: 8px !important;
}

.med-check-row {
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
  font-size: 12px !important;
  color: var(--text-secondary) !important;
}

.med-check-row .time-tag {
  margin-left: auto !important;
  font-size: 10.5px !important;
  font-weight: 600 !important;
  color: #059669 !important;
}

.med-check-row.pending .time-tag.pending {
  color: #f59e0b !important;
}

/* Estado de Bienestar */
.patient-mood-status-row {
  margin-bottom: 6px !important;
}

.mood-badge {
  display: inline-flex !important;
  align-items: center !important;
  gap: 6px !important;
  padding: 3px 10px !important;
  border-radius: 999px !important;
  font-size: 11.5px !important;
  font-weight: 700 !important;
}

.mood-badge.mood-good {
  background: #ecfdf5 !important;
  color: #047857 !important;
  border: 1px solid #a7f3d0 !important;
}

.followup-report-text {
  font-size: 12px !important;
  color: var(--text-secondary) !important;
  margin: 0 !important;
  line-height: 1.4 !important;
}

/* Señales de Alerta */
.alert-signals-row {
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
  flex-wrap: wrap !important;
  margin-bottom: 8px !important;
}

.signal-badge {
  display: inline-flex !important;
  align-items: center !important;
  gap: 5px !important;
  background: #ffffff !important;
  border: 1px solid #cde0f1 !important;
  padding: 3px 9px !important;
  border-radius: 999px !important;
  font-size: 11px !important;
  font-weight: 600 !important;
  color: #1e293b !important;
}

[data-theme="dark"] .signal-badge {
  background: #152244 !important;
  border-color: #2e4a87 !important;
  color: #f8fafc !important;
}

.signal-badge.ok .signal-dot {
  width: 7px !important;
  height: 7px !important;
  border-radius: 50% !important;
  background: #10b981 !important;
}

.triage-security-footer {
  display: flex !important;
  align-items: center !important;
  gap: 6px !important;
  font-size: 11.5px !important;
  color: #047857 !important;
}
"""

def update_css(base_dir):
    p = os.path.join(base_dir, "frontend", "style.css")
    if not os.path.exists(p):
        return
    with open(p, "r", encoding="utf-8") as f:
        content = f.read()

    marker = "/* ==========================================================================\n   NUEVA CONSULTA: ARQUITECTURA DE 3 COLUMNAS MODULAR"
    if marker in content:
        idx = content.find(marker)
        content = content[:idx] + THREE_COLUMN_CSS.strip() + "\n"
    else:
        content = content + "\n\n" + THREE_COLUMN_CSS.strip() + "\n"

    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Updated style.css with 3-column architecture in: {p}")

for root in ROOTS:
    update_index_html(root)
    update_css(root)

print("All files updated successfully.")
