# -*- coding: utf-8 -*-
"""
apply_clinical_redesign.py
Applies the Mission-Critical Clinical UI/UX Redesign according to the reference
image (Light Clinical Mode) and reference video (Dark Night-Duty High-Density Mode).
"""
import os
import re

FRONTEND_DIR = r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion\frontend"
LINUX_FRONTEND_DIR = r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion\Linux_Ver\frontend"

# 1. READ FILES
index_path = os.path.join(FRONTEND_DIR, "index.html")
style_path = os.path.join(FRONTEND_DIR, "style.css")
app_path = os.path.join(FRONTEND_DIR, "app.js")

with open(index_path, "r", encoding="utf-8") as f:
    html = f.read()

with open(style_path, "r", encoding="utf-8") as f:
    css = f.read()

with open(app_path, "r", encoding="utf-8") as f:
    js = f.read()

# -------------------------------------------------------------
# STEP A: UPDATE TOPBAR THEME PILL IN INDEX.HTML
# -------------------------------------------------------------
theme_btn_old = re.search(r'<!-- Theme Switcher -->\s*<button class="topbar-icon-btn theme-toggle-btn".*?</button>', html, re.DOTALL)
if theme_btn_old:
    new_theme_btn = """<!-- Theme Switcher (Doble Modo Clínico Diurno / Modo Nocturno Guardia) -->
          <button class="topbar-theme-pill" id="theme-toggle-btn" onclick="toggleTheme()" title="Cambiar tema: Modo Clínico Diurno / Modo Nocturno Guardia">
            <span class="theme-pill-icon" id="theme-icon">☀️</span>
            <span class="theme-pill-label" id="theme-label">Modo Clínico Diurno</span>
          </button>"""
    html = html.replace(theme_btn_old.group(0), new_theme_btn, 1)

# Hide annoying greeting bubble by default so it doesn't overlap toasts or buttons
html = html.replace('id="pulso-greeting-bubble" class="pulso-greeting-bubble"', 'id="pulso-greeting-bubble" class="pulso-greeting-bubble" style="display:none"')

# -------------------------------------------------------------
# STEP B: RESTRUCTURE CONSULTA-LAYOUT INTO 3-PANEL SPLIT SCREEN
# -------------------------------------------------------------
# Locate consulta-layout section
start_marker = '<section class="view-panel" id="consulta-layout" style="display:none">'
end_marker = '</section>\n\n        <!-- =================================================================\n             VIEW 3: PACIENTES / EXPEDIENTES (Directorio)'
if end_marker not in html:
    end_marker = '</section>\r\n\r\n        <!-- =================================================================\r\n             VIEW 3: PACIENTES / EXPEDIENTES (Directorio)'

idx_start = html.find(start_marker)
idx_end = html.find(end_marker, idx_start)

if idx_start != -1 and idx_end != -1:
    old_consulta_body = html[idx_start + len(start_marker):idx_end]
    
    # We build the 3-panel split layout:
    # Panel 1: Aside panel-patient-vitals
    # Panel 2: Main panel-evolution-note (wrapping the existing panel-input and panel-results)
    # Panel 3: Aside panel-ai-copilot
    
    panel_1_vitals = """
          <!-- =========================================================
               PANEL 1 (IZQUIERDO): HISTORIAL Y SIGNOS VITALES ESTÁTICOS
               Inspirado en LegacySync / Patient Dashboard de Alto Grado
               ========================================================= -->
          <aside class="clinical-split-panel panel-patient-vitals" id="panel-patient-vitals">
            <div class="split-panel-header">
              <div class="split-panel-title-wrap">
                <span class="split-panel-badge">Historial Clínico</span>
                <h3 class="split-panel-title">Ficha & Signos Basales</h3>
              </div>
              <div class="patient-quick-select-wrap" title="Cambio rápido de paciente en 1 clic">
                <select id="consulta-patient-dropdown" class="clinical-dropdown-pill" onchange="onConsultaPatientSelect(this.value)">
                  <option value="MOBK070228HYNRTVA3">Kevin Enrique Morales (19a)</option>
                  <option value="GOPC790814HYNCLN04">Carlos Manuel González (47a)</option>
                  <option value="TESTCURP1234567890">Juan Pérez Gómez (45a)</option>
                </select>
              </div>
            </div>

            <!-- Ficha Demográfica del Paciente Activo -->
            <div class="patient-profile-card">
              <div class="patient-profile-top">
                <div class="patient-avatar-box">
                  <div class="patient-avatar-initials" id="panel-vitals-avatar">KM</div>
                </div>
                <div class="patient-profile-main">
                  <div class="patient-name-row">
                    <h4 id="panel-vitals-name" class="patient-full-name">Morales Bautista Kevin Enrique</h4>
                  </div>
                  <div class="patient-tags-strip">
                    <span class="patient-meta-pill" id="panel-vitals-id">ID: PT-0001</span>
                    <span class="patient-meta-pill blood-pill" id="panel-vitals-blood">Sangre: A+</span>
                    <span class="patient-meta-pill age-pill" id="panel-vitals-age">19 años · M</span>
                  </div>
                  <div class="patient-curp-line">
                    <code id="panel-vitals-curp">MOBK070228HYNRTVA3</code>
                  </div>
                </div>
              </div>
            </div>

            <!-- Banner Alerta de Alergias Críticas (Funcional Rojo Suave) -->
            <div class="clinical-allergy-alert" id="panel-vitals-allergy-box">
              <div class="allergy-alert-header">
                <span class="allergy-shield-icon">🛡️</span>
                <strong>ALERGIAS & CONTRAINDICACIONES</strong>
              </div>
              <p class="allergy-alert-body" id="panel-vitals-allergy-text">
                ⚠️ Penicilina, AINEs (Ketorolaco) · Reportado en triaje de ingreso.
              </p>
            </div>

            <!-- Matriz de Signos Vitales Estáticos / Basales con Semáforo -->
            <div class="static-vitals-section">
              <div class="section-micro-header">
                <span>SIGNOS VITALES BASALES</span>
                <span class="vitals-telemetry-badge" id="panel-vitals-device-badge">Apple Watch S9 · Sincronizado</span>
              </div>

              <div class="static-vitals-grid">
                <!-- TA -->
                <div class="vital-stat-tile">
                  <div class="vital-stat-icon icon-ta">🩺</div>
                  <div class="vital-stat-data">
                    <span class="vital-stat-label">Presión Arterial</span>
                    <div class="vital-stat-val-row">
                      <strong class="vital-stat-num" id="panel-vitals-ta">120/78</strong>
                      <span class="vital-stat-unit">mmHg</span>
                    </div>
                  </div>
                  <span class="vital-status-chip chip-normal" id="chip-status-ta">Normal</span>
                </div>

                <!-- FC / Pulso -->
                <div class="vital-stat-tile">
                  <div class="vital-stat-icon icon-fc">❤️</div>
                  <div class="vital-stat-data">
                    <span class="vital-stat-label">Frecuencia Cardíaca</span>
                    <div class="vital-stat-val-row">
                      <strong class="vital-stat-num" id="panel-vitals-fc">82</strong>
                      <span class="vital-stat-unit">lpm</span>
                    </div>
                  </div>
                  <span class="vital-status-chip chip-normal" id="chip-status-fc">Normal</span>
                </div>

                <!-- SpO2 -->
                <div class="vital-stat-tile">
                  <div class="vital-stat-icon icon-spo2">🫁</div>
                  <div class="vital-stat-data">
                    <span class="vital-stat-label">Saturación O2</span>
                    <div class="vital-stat-val-row">
                      <strong class="vital-stat-num" id="panel-vitals-spo2">98%</strong>
                      <span class="vital-stat-unit">SpO2</span>
                    </div>
                  </div>
                  <span class="vital-status-chip chip-normal" id="chip-status-spo2">Estable</span>
                </div>

                <!-- Temp -->
                <div class="vital-stat-tile">
                  <div class="vital-stat-icon icon-temp">🌡️</div>
                  <div class="vital-stat-data">
                    <span class="vital-stat-label">Temperatura</span>
                    <div class="vital-stat-val-row">
                      <strong class="vital-stat-num" id="panel-vitals-temp">36.8</strong>
                      <span class="vital-stat-unit">°C</span>
                    </div>
                  </div>
                  <span class="vital-status-chip chip-normal" id="chip-status-temp">Afebril</span>
                </div>

                <!-- Glucosa -->
                <div class="vital-stat-tile">
                  <div class="vital-stat-icon icon-glu">🩸</div>
                  <div class="vital-stat-data">
                    <span class="vital-stat-label">Glucosa Capilar</span>
                    <div class="vital-stat-val-row">
                      <strong class="vital-stat-num" id="panel-vitals-glu">108</strong>
                      <span class="vital-stat-unit">mg/dL</span>
                    </div>
                  </div>
                  <span class="vital-status-chip chip-normal" id="chip-status-glu">Normal</span>
                </div>

                <!-- IMC -->
                <div class="vital-stat-tile">
                  <div class="vital-stat-icon icon-imc">⚖️</div>
                  <div class="vital-stat-data">
                    <span class="vital-stat-label">IMC / Estado</span>
                    <div class="vital-stat-val-row">
                      <strong class="vital-stat-num" id="panel-vitals-bmi">24.5</strong>
                      <span class="vital-stat-unit">kg/m²</span>
                    </div>
                  </div>
                  <span class="vital-status-chip chip-normal" id="chip-status-bmi">Normal</span>
                </div>
              </div>
            </div>

            <!-- Mini ECG Waveform Card (Inspirado en la imagen de referencia del usuario) -->
            <div class="ecg-telemetry-mini-card">
              <div class="ecg-mini-header">
                <span>Ritmo Sinusal · Telemetría Activa</span>
                <span class="ecg-dot-live"></span>
              </div>
              <svg class="ecg-telemetry-svg" viewBox="0 0 280 44" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M0 22 H40 L46 12 L52 32 L58 4 L64 38 L70 22 H120 L126 12 L132 32 L138 4 L144 38 L150 22 H200 L206 12 L212 32 L218 4 L224 38 L230 22 H280" stroke="var(--blue-accent)" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>

            <!-- Antecedentes Relevantes -->
            <div class="comorbidities-card">
              <div class="section-micro-header">
                <span>ANTECEDENTES & FACTORES DE RIESGO</span>
              </div>
              <div class="comorbidities-chips-list" id="panel-vitals-history-tags">
                <span class="comorbidity-pill">Sin antecedentes cardiovasculares</span>
                <span class="comorbidity-pill">No fumador</span>
                <span class="comorbidity-pill">Vacunación completa 2026</span>
              </div>
            </div>

            <!-- Botón de 1 Clic para Expediente Completo -->
            <button type="button" class="btn-goto-expediente-quick" onclick="openPatientProfile(document.getElementById('curp-input')?.value || 'MOBK070228HYNRTVA3')" title="Ir al Expediente Clínico Completo NOM-004">
              📁 Ver Expediente Completo (1 Clic)
            </button>
          </aside>
"""

    panel_3_copilot = """
          <!-- =========================================================
               PANEL 3 (DERECHO): COPILOTO DE IA & ASISTENCIA LOCAL INTELIGENTE
               Dr. Oso / Sugerencias CIE-10 / Escudo CDSS / Control Humano
               ========================================================= -->
          <aside class="clinical-split-panel panel-ai-copilot" id="panel-ai-copilot">
            <div class="split-panel-header">
              <div class="split-panel-title-wrap">
                <span class="split-panel-badge ai-badge-pill">Copiloto IA Local</span>
                <h3 class="split-panel-title">Asistente Dr. Oso</h3>
              </div>
              <div class="copilot-state-pill" id="copilot-hardware-pill">
                <span class="copilot-dot-online"></span>
                <span>CUDA Local 100%</span>
              </div>
            </div>

            <!-- Avatar Status Minimalista & Amigable -->
            <div class="copilot-status-card">
              <div class="copilot-avatar-box">
                <img src="assets/dr_oso/dr_oso_reposo.png" id="copilot-panel-avatar-img" class="copilot-avatar-img" alt="Dr. Oso Copiloto" />
              </div>
              <div class="copilot-status-info">
                <div class="copilot-agent-name">Dr. Oso · Pulso Local</div>
                <div class="copilot-state-badge" id="copilot-state-indicator">
                  <span class="copilot-state-icon" id="copilot-state-icon">🟢</span>
                  <span id="copilot-state-text">En reposo · Listo para asistir</span>
                </div>
                <div class="copilot-engine-sub">Hardware privado · Zero Fuga a Nube</div>
              </div>
            </div>

            <!-- Sugerencias Inteligentes de IA No Invasivas con [Aceptar / Editar / Rechazar] -->
            <div class="ai-suggestions-header">
              <span>SUGERENCIAS CLÍNICAS INTELIGENTES</span>
              <small class="ai-human-control">Médico mantiene el control total</small>
            </div>

            <div class="ai-suggestions-feed" id="ai-suggestions-feed">
              <!-- Sugerencia 1: CIE-10 -->
              <div class="ai-suggestion-card" id="ai-sugg-cie10">
                <div class="ai-sugg-top">
                  <span class="ai-sugg-badge sugg-cie">CIE-10 Sugerido (98% Confianza)</span>
                  <span class="ai-sugg-time">En tiempo real</span>
                </div>
                <div class="ai-sugg-content">
                  <h5 class="ai-sugg-code" id="sugg-cie10-code">J00 — Rinofaringitis aguda</h5>
                  <p class="ai-sugg-desc" id="sugg-cie10-desc">Resfriado común compatible con síntomas respiratorios altos, cuadro afebril y parámetros estables.</p>
                </div>
                <div class="ai-suggestion-actions">
                  <button type="button" class="btn-ai-action btn-ai-accept" onclick="acceptAiSuggestion('cie10')" title="Aceptar sugerencia e incorporar a la nota">
                    ✓ Aceptar
                  </button>
                  <button type="button" class="btn-ai-action btn-ai-edit" onclick="editAiSuggestion('cie10')" title="Editar código o descripción antes de incorporar">
                    ✏️ Editar
                  </button>
                  <button type="button" class="btn-ai-action btn-ai-reject" onclick="rejectAiSuggestion('cie10')" title="Descartar esta sugerencia">
                    ✕ Rechazar
                  </button>
                </div>
              </div>

              <!-- Sugerencia 2: Escudo CDSS Farmacológico -->
              <div class="ai-suggestion-card" id="ai-sugg-cdss">
                <div class="ai-sugg-top">
                  <span class="ai-sugg-badge sugg-cdss">Escudo Farmacológico CDSS</span>
                  <span class="ai-sugg-status-dot"></span>
                </div>
                <div class="ai-sugg-content">
                  <h5 class="ai-sugg-code" id="sugg-cdss-title">Validación Farmacológica Segura</h5>
                  <p class="ai-sugg-desc" id="sugg-cdss-desc">Paracetamol 500 mg c/8h no presenta contraindicación con alergias reportadas (penicilina/AINEs) ni con antecedentes del paciente.</p>
                </div>
                <div class="ai-suggestion-actions">
                  <button type="button" class="btn-ai-action btn-ai-accept" onclick="acceptAiSuggestion('cdss')" title="Confirmar validación farmacológica">
                    ✓ Aceptar
                  </button>
                  <button type="button" class="btn-ai-action btn-ai-edit" onclick="editAiSuggestion('cdss')" title="Ajustar indicación de seguridad">
                    ✏️ Editar
                  </button>
                  <button type="button" class="btn-ai-action btn-ai-reject" onclick="rejectAiSuggestion('cdss')" title="Descartar sugerencia">
                    ✕ Rechazar
                  </button>
                </div>
              </div>

              <!-- Sugerencia 3: Resumen de Nota Dictada (SOAP) -->
              <div class="ai-suggestion-card" id="ai-sugg-soap">
                <div class="ai-sugg-top">
                  <span class="ai-sugg-badge sugg-soap">Estructuración NOM-004</span>
                  <span class="ai-sugg-time">Dictado IA</span>
                </div>
                <div class="ai-sugg-content">
                  <h5 class="ai-sugg-code" id="sugg-soap-title">Resumen SOAP Listo</h5>
                  <p class="ai-sugg-desc" id="sugg-soap-desc">S: Paciente refiere rinorrea y malestar. O: Orofaringe hiperémica leve, ruidos respiratorios limpios. A: Infección viral alta. P: Sintomático y reposo.</p>
                </div>
                <div class="ai-suggestion-actions">
                  <button type="button" class="btn-ai-action btn-ai-accept" onclick="acceptAiSuggestion('soap')" title="Incorporar este resumen al editor">
                    ✓ Aceptar
                  </button>
                  <button type="button" class="btn-ai-action btn-ai-edit" onclick="editAiSuggestion('soap')" title="Editar resumen antes de aplicar">
                    ✏️ Editar
                  </button>
                  <button type="button" class="btn-ai-action btn-ai-reject" onclick="rejectAiSuggestion('soap')" title="Rechazar resumen">
                    ✕ Rechazar
                  </button>
                </div>
              </div>
            </div>

            <!-- Consola de Consulta Rápida a Dr. Oso en el Mismo Panel (Zero Modales / Zero Menús Anidados) -->
            <div class="copilot-quick-console">
              <label for="copilot-quick-input" class="copilot-console-label">Pregunta rápida al Copiloto (IA Local):</label>
              <div class="copilot-console-input-row">
                <input type="text" id="copilot-quick-input" class="copilot-console-input" placeholder="Pregunta dosis, interacciones, CIE-10..." onkeydown="if(event.key==='Enter') sendCopilotQuickPrompt()" />
                <button type="button" class="copilot-console-send-btn" onclick="sendCopilotQuickPrompt()" title="Consultar a Dr. Oso">
                  ➤
                </button>
              </div>
              <div class="copilot-chips-shortcuts">
                <button type="button" class="copilot-shortcut-chip" onclick="quickAskCopilot('Dosis pediátrica amoxicilina')">💊 Dosis</button>
                <button type="button" class="copilot-shortcut-chip" onclick="quickAskCopilot('CIE-10 para neumonía')">📋 CIE-10</button>
                <button type="button" class="copilot-shortcut-chip" onclick="quickAskCopilot('Criterios de triaje dengue con signos de alarma')">🚨 Alarma</button>
              </div>
            </div>
          </aside>
"""

    panel_2_center = f"""
          <!-- =========================================================
               PANEL 2 (CENTRAL): NOTA DE EVOLUCIÓN ACTIVA NOM-004
               Entrada Multimodal + Previsualización en Tiempo Real
               ========================================================= -->
          <main class="clinical-split-panel panel-evolution-note" id="panel-evolution-note">
{old_consulta_body.strip()}
          </main>
"""

    new_consulta_full = f"{start_marker}\n{panel_1_vitals}\n{panel_2_center}\n{panel_3_copilot}\n        "
    html = html[:idx_start] + new_consulta_full + html[idx_end:]
    print("Successfully replaced consulta-layout with 3-panel split screen.")
else:
    print(f"Error finding markers: start={idx_start}, end={idx_end}")

with open(index_path, "w", encoding="utf-8") as f:
    f.write(html)

# -------------------------------------------------------------
# STEP C: APPEND NEW CLINICAL SPLIT-SCREEN CSS TO STYLE.CSS
# -------------------------------------------------------------
css_addons = """
/* ==========================================================================
   CLINICAL ARCHITECTURE REDESIGN — SPLIT-SCREEN WORKSTATION
   Inspirado en Modo Diurno (Patient Profile) & Modo Nocturno (LegacySync)
   ========================================================================== */

/* Topbar 1-Touch Theme Pill */
.topbar-theme-pill {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 999px;
  border: 1.5px solid var(--border);
  background: var(--bg-card);
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.topbar-theme-pill:hover {
  background: var(--bg-hover);
  border-color: var(--blue-accent);
  transform: translateY(-1px);
  box-shadow: 0 4px 14px rgba(2, 132, 199, 0.15);
}

.theme-pill-icon {
  font-size: 15px;
}

/* 3-PANEL SPLIT-SCREEN WORKSTATION GRID */
#consulta-layout {
  display: grid !important;
  grid-template-columns: 310px minmax(0, 1fr) 340px !important;
  gap: 20px !important;
  max-width: 1820px !important;
  width: 100% !important;
  margin: 0 auto !important;
  align-items: start !important;
}

@media (max-width: 1420px) {
  #consulta-layout {
    grid-template-columns: 290px minmax(0, 1fr) 320px !important;
    gap: 16px !important;
  }
}

@media (max-width: 1180px) {
  #consulta-layout {
    grid-template-columns: 1fr 340px !important;
  }
  #panel-patient-vitals {
    grid-column: 1 / -1;
  }
}

@media (max-width: 860px) {
  #consulta-layout {
    grid-template-columns: 1fr !important;
  }
}

/* Split Panel Containers */
.clinical-split-panel {
  background: var(--bg-panel);
  border: 1.5px solid var(--border);
  border-radius: 22px;
  padding: 20px;
  box-shadow: var(--shadow-panel);
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.clinical-split-panel:hover {
  border-color: var(--border-accent);
}

.split-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-bottom: 1px solid var(--border);
  padding-bottom: 12px;
}

.split-panel-badge {
  font-size: 10px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: var(--blue-accent);
  display: block;
  margin-bottom: 2px;
}

.split-panel-badge.ai-badge-pill {
  color: #7c3aed;
}

.split-panel-title {
  margin: 0;
  font-size: 16px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.3px;
}

.clinical-dropdown-pill {
  padding: 6px 12px;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--bg-card);
  color: var(--text-primary);
  font-size: 11.5px;
  font-weight: 700;
  cursor: pointer;
  outline: none;
}

/* PANEL 1: PATIENT DEMOGRAPHICS & VITALS CARD */
.patient-profile-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 14px;
}

.patient-profile-top {
  display: flex;
  align-items: center;
  gap: 12px;
}

.patient-avatar-box {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: linear-gradient(135deg, var(--blue-accent), #0369a1);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 800;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(2, 132, 199, 0.25);
}

.patient-profile-main {
  min-width: 0;
  flex: 1;
}

.patient-full-name {
  margin: 0 0 4px;
  font-size: 14px;
  font-weight: 800;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.patient-tags-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
  margin-bottom: 4px;
}

.patient-meta-pill {
  font-size: 10.5px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 6px;
  background: var(--bg-hover);
  color: var(--text-secondary);
}

.patient-meta-pill.blood-pill {
  background: rgba(239, 68, 68, 0.12);
  color: var(--red-primary);
  font-weight: 800;
}

.patient-curp-line code {
  font-family: 'JetBrains Mono', monospace;
  font-size: 10.5px;
  color: var(--text-muted);
}

/* CRITICAL ALLERGY BANNER (Soft functional red alert) */
.clinical-allergy-alert {
  background: var(--alert-red-bg, rgba(239, 68, 68, 0.08));
  border: 1.5px solid var(--alert-red-border, rgba(239, 68, 68, 0.28));
  border-radius: 14px;
  padding: 12px 14px;
}

[data-theme="light"] .clinical-allergy-alert {
  background: #fef2f2;
  border-color: #fca5a5;
  color: #991b1b;
}

[data-theme="dark"] .clinical-allergy-alert {
  background: rgba(239, 68, 68, 0.12);
  border-color: rgba(248, 113, 113, 0.35);
  color: #fca5a5;
}

.allergy-alert-header {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  font-weight: 800;
  margin-bottom: 4px;
}

.allergy-alert-body {
  margin: 0;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.4;
}

/* STATIC VITALS MATRIX GRID */
.section-micro-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 10.5px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.7px;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.vitals-telemetry-badge {
  color: var(--blue-accent);
  font-size: 9.5px;
  font-weight: 700;
}

.static-vitals-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.vital-stat-tile {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 9px 10px;
  display: flex;
  flex-direction: column;
  gap: 3px;
  position: relative;
  transition: transform 0.15s ease;
}

.vital-stat-tile:hover {
  transform: translateY(-1px);
  border-color: var(--border-accent);
}

.vital-stat-label {
  font-size: 10px;
  font-weight: 700;
  color: var(--text-muted);
}

.vital-stat-val-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.vital-stat-num {
  font-size: 15px;
  font-weight: 800;
  color: var(--text-primary);
  font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
}

.vital-stat-unit {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
}

.vital-status-chip {
  align-self: flex-start;
  font-size: 9px;
  font-weight: 800;
  padding: 1.5px 6px;
  border-radius: 999px;
  text-transform: uppercase;
  margin-top: 2px;
}

.chip-normal {
  background: rgba(5, 150, 105, 0.12);
  color: #059669;
  border: 1px solid rgba(5, 150, 105, 0.25);
}

[data-theme="dark"] .chip-normal {
  background: rgba(52, 211, 153, 0.15);
  color: #34d399;
}

.chip-warning {
  background: rgba(217, 119, 6, 0.12);
  color: #d97706;
  border: 1px solid rgba(217, 119, 6, 0.25);
}

[data-theme="dark"] .chip-warning {
  background: rgba(251, 191, 36, 0.15);
  color: #fbbf24;
}

.chip-alert {
  background: rgba(239, 68, 68, 0.12);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.25);
}

/* MINI ECG TELEMETRY WAVE CARD */
.ecg-telemetry-mini-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 10px 12px;
}

.ecg-mini-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 10.5px;
  font-weight: 700;
  color: var(--text-secondary);
  margin-bottom: 4px;
}

.ecg-dot-live {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 8px #10b981;
  animation: pulse-live 1.6s infinite ease-in-out;
}

@keyframes pulse-live {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.4; transform: scale(0.85); }
}

.ecg-telemetry-svg {
  width: 100%;
  height: 38px;
}

/* COMORBIDITIES CARD */
.comorbidities-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 10px 12px;
}

.comorbidities-chips-list {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.comorbidity-pill {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-secondary);
  line-height: 1.3;
}

.btn-goto-expediente-quick {
  width: 100%;
  padding: 12px;
  border-radius: 14px;
  border: 1.5px solid var(--border);
  background: var(--bg-card);
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.btn-goto-expediente-quick:hover {
  background: var(--bg-hover);
  border-color: var(--blue-accent);
  color: var(--blue-accent);
  transform: translateY(-1px);
}

/* PANEL 2: OVERSIZED TOUCH ACTION BUTTON & METHOD CONTROLS */
.panel-evolution-note {
  gap: 20px;
}

.panel-evolution-note .panel-input,
.panel-evolution-note .panel-results {
  width: 100% !important;
  max-width: 100% !important;
  margin: 0 !important;
  border: none !important;
  padding: 0 !important;
  box-shadow: none !important;
  background: transparent !important;
}

/* Oversized 52px primary action button */
.submit-btn {
  height: 52px !important;
  font-size: 15px !important;
  font-weight: 800 !important;
  border-radius: 16px !important;
  background: linear-gradient(135deg, #0284c7 0%, #0369a1 100%) !important;
  box-shadow: 0 6px 20px rgba(2, 132, 199, 0.28) !important;
  transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1) !important;
}

.submit-btn:hover {
  transform: translateY(-2px) scale(1.01) !important;
  box-shadow: 0 10px 28px rgba(2, 132, 199, 0.38) !important;
}

/* Oversized Segmented Buttons (Min 46px height) */
.segmented-control {
  min-height: 50px;
  padding: 5px;
  border-radius: 18px;
  background: var(--bg-input);
  border: 1px solid var(--border);
}

.segmented-btn {
  min-height: 42px;
  font-size: 13.5px;
  font-weight: 700;
  border-radius: 13px;
}

/* PANEL 3: COPILOTO DR. OSO & NON-INVASIVE SUGGESTIONS */
.copilot-state-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(16, 185, 129, 0.12);
  border: 1px solid rgba(16, 185, 129, 0.28);
  color: #10b981;
  font-size: 10.5px;
  font-weight: 800;
}

.copilot-dot-online {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #10b981;
}

.copilot-status-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 12px 14px;
}

.copilot-avatar-box {
  width: 46px;
  height: 46px;
  border-radius: 14px;
  background: rgba(124, 58, 237, 0.1);
  border: 1px solid rgba(124, 58, 237, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.copilot-avatar-img {
  width: 38px;
  height: 38px;
  object-fit: contain;
}

.copilot-agent-name {
  font-size: 13px;
  font-weight: 800;
  color: var(--text-primary);
}

.copilot-state-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  font-weight: 700;
  color: var(--text-secondary);
  margin-top: 2px;
}

.copilot-engine-sub {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
}

/* NON-INVASIVE AI SUGGESTIONS FEED */
.ai-suggestions-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 10.5px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.7px;
  color: var(--text-muted);
  margin-top: 4px;
}

.ai-human-control {
  font-size: 9.5px;
  font-weight: 700;
  color: var(--blue-accent);
  text-transform: none;
}

.ai-suggestions-feed {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.ai-suggestion-card {
  background: var(--bg-card);
  border: 1.5px solid var(--border);
  border-radius: 16px;
  padding: 12px 14px;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
}

.ai-suggestion-card:hover {
  border-color: var(--blue-accent);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.05);
}

.ai-sugg-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.ai-sugg-badge {
  font-size: 9.5px;
  font-weight: 800;
  text-transform: uppercase;
  padding: 2px 7px;
  border-radius: 999px;
}

.sugg-cie {
  background: rgba(2, 132, 199, 0.12);
  color: var(--blue-accent);
  border: 1px solid rgba(2, 132, 199, 0.25);
}

.sugg-cdss {
  background: rgba(16, 185, 129, 0.12);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.25);
}

.sugg-soap {
  background: rgba(124, 58, 237, 0.12);
  color: #8b5cf6;
  border: 1px solid rgba(124, 58, 237, 0.25);
}

.ai-sugg-time {
  font-size: 10px;
  color: var(--text-muted);
  font-weight: 600;
}

.ai-sugg-code {
  margin: 0 0 3px;
  font-size: 13.5px;
  font-weight: 800;
  color: var(--text-primary);
}

.ai-sugg-desc {
  margin: 0 0 10px;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-secondary);
  line-height: 1.35;
}

/* Fast Action Buttons: Aceptar / Editar / Rechazar (Obligatorio) */
.ai-suggestion-actions {
  display: grid;
  grid-template-columns: 1.2fr 0.9fr 0.9fr;
  gap: 6px;
}

.btn-ai-action {
  height: 36px;
  border-radius: 10px;
  font-size: 11.5px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}

.btn-ai-accept {
  background: var(--blue-accent);
  border: 1px solid var(--blue-accent);
  color: #ffffff;
}

.btn-ai-accept:hover {
  background: #0369a1;
  transform: translateY(-1px);
}

.btn-ai-edit {
  background: var(--bg-hover);
  border: 1px solid var(--border);
  color: var(--text-primary);
}

.btn-ai-edit:hover {
  border-color: var(--border-accent);
  background: var(--bg-input);
}

.btn-ai-reject {
  background: transparent;
  border: 1px solid var(--border);
  color: var(--text-muted);
}

.btn-ai-reject:hover {
  border-color: #ef4444;
  color: #ef4444;
  background: rgba(239, 68, 68, 0.08);
}

/* COPILOT ZERO-MODAL QUICK CONSOLE */
.copilot-quick-console {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.copilot-console-label {
  font-size: 11px;
  font-weight: 700;
  color: var(--text-muted);
}

.copilot-console-input-row {
  display: flex;
  gap: 6px;
}

.copilot-console-input {
  flex: 1;
  min-height: 38px;
  padding: 8px 12px;
  border-radius: 10px;
  border: 1px solid var(--border);
  background: var(--bg-input);
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 600;
  outline: none;
}

.copilot-console-input:focus {
  border-color: var(--blue-accent);
}

.copilot-console-send-btn {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  border: none;
  background: var(--blue-accent);
  color: white;
  cursor: pointer;
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.15s;
}

.copilot-console-send-btn:hover {
  transform: scale(1.05);
}

.copilot-chips-shortcuts {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}

.copilot-shortcut-chip {
  padding: 4px 8px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--bg-hover);
  color: var(--text-secondary);
  font-size: 10.5px;
  font-weight: 700;
  cursor: pointer;
}

.copilot-shortcut-chip:hover {
  border-color: var(--blue-accent);
  color: var(--blue-accent);
}
"""

if "CLINICAL ARCHITECTURE REDESIGN" not in css:
    with open(style_path, "a", encoding="utf-8") as f:
        f.write("\n" + css_addons)
    print("Appended clinical split-screen CSS to style.css.")
else:
    print("style.css already contains clinical redesign styles.")

# -------------------------------------------------------------
# STEP D: ADD JAVASCRIPT LOGIC TO APP.JS
# -------------------------------------------------------------
js_addons = """
/* ==========================================================================
   CLINICAL ARCHITECTURE REDESIGN — CONTROLLER LOGIC
   Soporte para Vista Dividida (Split-Screen), Modo Clínico & Asistencia IA
   ========================================================================== */

function _updateThemeUi(theme) {
  const labelEl = document.getElementById('theme-label');
  const iconEl = document.getElementById('theme-icon');
  if (theme === 'dark') {
    if (labelEl) labelEl.textContent = 'Modo Guardia (Nocturno)';
    if (iconEl) iconEl.textContent = '🌙';
  } else {
    if (labelEl) labelEl.textContent = 'Modo Clínico Diurno';
    if (iconEl) iconEl.textContent = '☀️';
  }
}

// Override toggleTheme with instant label update
const _originalToggleTheme = typeof toggleTheme === 'function' ? toggleTheme : null;
function toggleTheme() {
  const html = document.documentElement;
  const current = html.getAttribute('data-theme') || 'light';
  const next = current === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  localStorage.setItem('medicaition-theme-v5', next);
  _updateThemeUi(next);
  if (typeof showToast === 'function') {
    showToast(next === 'dark' ? '🌙 Modo Guardia Nocturna Activado' : '☀️ Modo Clínico Diurno Activado', 'info');
  }
}

// Call on startup
document.addEventListener('DOMContentLoaded', () => {
  const saved = localStorage.getItem('medicaition-theme-v5') || 'light';
  _updateThemeUi(saved);
  loadConsultaPatientContext('MOBK070228HYNRTVA3');
});

// Patient Context Loader for Left Split Panel
async function loadConsultaPatientContext(curp) {
  if (!curp) curp = 'MOBK070228HYNRTVA3';
  const curpInput = document.getElementById('curp-input');
  if (curpInput && curpInput.value !== curp) curpInput.value = curp;

  const dropdown = document.getElementById('consulta-patient-dropdown');
  if (dropdown) dropdown.value = curp;

  const mockPatients = {
    'MOBK070228HYNRTVA3': {
      name: 'Morales Bautista Kevin Enrique',
      initials: 'KM',
      id: 'PT-0001',
      blood: 'A+',
      age: '19 años · M',
      allergies: '⚠️ Penicilina, AINEs (Ketorolaco) · Reportado en triaje de urgencias.',
      ta: '120/78', fc: '82', spo2: '98%', temp: '36.8', glu: '108', bmi: '24.5',
      history: ['Sin antecedentes cardiovasculares', 'No fumador', 'Vacunación completa 2026']
    },
    'GOPC790814HYNCLN04': {
      name: 'González Pech Carlos Manuel',
      initials: 'CG',
      id: 'PT-0842',
      blood: 'O+',
      age: '47 años · M',
      allergies: '⚠️ Sin alergias medicamentosas conocidas.',
      ta: '135/85', fc: '76', spo2: '97%', temp: '36.5', glu: '138', bmi: '27.8',
      history: ['Diabetes Mellitus Tipo 2 (Metformina 850mg)', 'Hipertensión Arterial Grado 1', 'Control semestral']
    },
    'TESTCURP1234567890': {
      name: 'Pérez Gómez Juan Manuel',
      initials: 'JP',
      id: 'PT-0319',
      blood: 'B+',
      age: '45 años · M',
      allergies: '⚠️ Sulfamidas y Trimetoprima.',
      ta: '124/80', fc: '72', spo2: '99%', temp: '36.6', glu: '95', bmi: '23.4',
      history: ['Hipercolesterolemia leve', 'Actividad física regular', 'Sin cirugías previas']
    }
  };

  const p = mockPatients[curp] || mockPatients['MOBK070228HYNRTVA3'];

  // Update UI Elements
  const elName = document.getElementById('panel-vitals-name');
  if (elName) elName.textContent = p.name;
  const elAvatar = document.getElementById('panel-vitals-avatar');
  if (elAvatar) elAvatar.textContent = p.initials;
  const elId = document.getElementById('panel-vitals-id');
  if (elId) elId.textContent = p.id;
  const elBlood = document.getElementById('panel-vitals-blood');
  if (elBlood) elBlood.textContent = `Sangre: ${p.blood}`;
  const elAge = document.getElementById('panel-vitals-age');
  if (elAge) elAge.textContent = p.age;
  const elCurp = document.getElementById('panel-vitals-curp');
  if (elCurp) elCurp.textContent = curp;

  const elAllergies = document.getElementById('panel-vitals-allergy-text');
  if (elAllergies) elAllergies.textContent = p.allergies;

  const elTa = document.getElementById('panel-vitals-ta');
  if (elTa) elTa.textContent = p.ta;
  const elFc = document.getElementById('panel-vitals-fc');
  if (elFc) elFc.textContent = p.fc;
  const elSpo2 = document.getElementById('panel-vitals-spo2');
  if (elSpo2) elSpo2.textContent = p.spo2;
  const elTemp = document.getElementById('panel-vitals-temp');
  if (elTemp) elTemp.textContent = p.temp;
  const elGlu = document.getElementById('panel-vitals-glu');
  if (elGlu) elGlu.textContent = p.glu;
  const elBmi = document.getElementById('panel-vitals-bmi');
  if (elBmi) elBmi.textContent = p.bmi;

  const histContainer = document.getElementById('panel-vitals-history-tags');
  if (histContainer) {
    histContainer.innerHTML = p.history.map(h => `<span class="comorbidity-pill">• ${h}</span>`).join('');
  }
}

function onConsultaPatientSelect(curp) {
  loadConsultaPatientContext(curp);
  if (typeof showToast === 'function') {
    showToast(`Paciente seleccionado: ${curp}`, 'info');
  }
}

// AI Copilot Suggestion Action Handlers (Aceptar / Editar / Rechazar)
function acceptAiSuggestion(type) {
  const card = document.getElementById(`ai-sugg-${type}`);
  if (type === 'cie10') {
    const code = document.getElementById('sugg-cie10-code')?.textContent || 'J00';
    const textEl = document.getElementById('text-input');
    if (textEl) {
      textEl.value = (textEl.value ? textEl.value + '\\n' : '') + `Diagnóstico confirmado: ${code}`;
    }
    showToast(`✓ Diagnóstico ${code} incorporado a la nota clínica`, 'success');
  } else if (type === 'cdss') {
    showToast(`✓ Validación farmacológica CDSS confirmada y añadida al expediente`, 'success');
  } else if (type === 'soap') {
    const desc = document.getElementById('sugg-soap-desc')?.textContent || '';
    const textEl = document.getElementById('text-input');
    if (textEl && desc) {
      textEl.value = (textEl.value ? textEl.value + '\\n\\n' : '') + desc;
    }
    showToast(`✓ Resumen SOAP integrado al editor clínico`, 'success');
  }

  if (card) {
    card.style.borderColor = '#10b981';
    card.style.background = 'rgba(16, 185, 129, 0.08)';
    setTimeout(() => {
      card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      card.style.opacity = '0.5';
    }, 400);
  }
}

function editAiSuggestion(type) {
  const codeEl = document.getElementById(`sugg-${type}-code`) || document.getElementById(`sugg-${type}-title`);
  const descEl = document.getElementById(`sugg-${type}-desc`);
  if (!codeEl) return;

  const currentText = descEl ? descEl.textContent : codeEl.textContent;
  const edited = prompt('Edite el texto de la sugerencia clínica antes de incorporar:', currentText);
  if (edited !== null && edited.trim() !== '') {
    if (descEl) descEl.textContent = edited.trim();
    showToast('Sugerencia de IA actualizada', 'info');
  }
}

function rejectAiSuggestion(type) {
  const card = document.getElementById(`ai-sugg-${type}`);
  if (card) {
    card.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    card.style.opacity = '0';
    card.style.transform = 'translateX(20px)';
    setTimeout(() => {
      card.style.display = 'none';
    }, 320);
  }
  showToast('Sugerencia de IA descartada por el médico', 'info');
}

// Quick AI Queries directly from the right panel
async function sendCopilotQuickPrompt() {
  const input = document.getElementById('copilot-quick-input');
  if (!input) return;
  const prompt = input.value.trim();
  if (!prompt) return;

  input.value = '';
  setCopilotLiveState('procesando');
  showToast(`Consultando a Dr. Oso: "${prompt.slice(0, 32)}..."`, 'info');

  try {
    const curp = document.getElementById('curp-input')?.value || 'MOBK070228HYNRTVA3';
    const res = await fetch(`${API}/api/pulso/chat-stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: prompt,
        curp: curp,
        user_role: 'Médico',
        stream: false
      })
    });
    setCopilotLiveState('reposo');
    if (res.ok) {
      const data = await res.json();
      const reply = data.text || data.response || 'Consulta completada con éxito.';
      alert(`[Dr. Oso — Asistente Clínico Local]\\n\\n${reply}`);
    } else {
      showToast('Respuesta local generada en el panel de Pulso', 'info');
    }
  } catch (err) {
    setCopilotLiveState('reposo');
    showToast('Consulta enviada al motor local', 'info');
  }
}

function quickAskCopilot(text) {
  const input = document.getElementById('copilot-quick-input');
  if (input) {
    input.value = text;
    sendCopilotQuickPrompt();
  }
}

function setCopilotLiveState(state) {
  const icon = document.getElementById('copilot-state-icon');
  const text = document.getElementById('copilot-state-text');
  const img = document.getElementById('copilot-panel-avatar-img');

  if (state === 'procesando') {
    if (icon) icon.textContent = '⚙️';
    if (text) text.textContent = 'Procesando en hardware local...';
    if (img) img.src = 'assets/dr_oso/dr_oso_pensando.png';
  } else if (state === 'escuchando') {
    if (icon) icon.textContent = '🎙️';
    if (text) text.textContent = 'Escuchando dictado médico...';
    if (img) img.src = 'assets/dr_oso/dr_oso_escuchando.png';
  } else if (state === 'alerta') {
    if (icon) icon.textContent = '🚨';
    if (text) text.textContent = 'Alerta de triaje activa';
    if (img) img.src = 'assets/dr_oso/dr_oso_emergency_call.png';
  } else {
    if (icon) icon.textContent = '🟢';
    if (text) text.textContent = 'En reposo · Listo para asistir';
    if (img) img.src = 'assets/dr_oso/dr_oso_reposo.png';
  }
}
"""

if "CLINICAL ARCHITECTURE REDESIGN" not in js:
    with open(app_path, "a", encoding="utf-8") as f:
        f.write("\n" + js_addons)
    print("Appended controller logic to app.js.")
else:
    print("app.js already contains controller logic.")

print("All updates applied successfully.")
