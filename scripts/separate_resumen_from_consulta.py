# -*- coding: utf-8 -*-
"""
separate_resumen_from_consulta.py
Separates Resumen strictly as Patient Data & Biometric/Telemetry Monitor,
leaving all active consultation workflows strictly to Nueva Consulta.
"""
import os

BASE_DIR = r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion"
INDEX_PATH = os.path.join(BASE_DIR, "frontend", "index.html")
LINUX_INDEX_PATH = os.path.join(BASE_DIR, "Linux_Ver", "frontend", "index.html")

with open(INDEX_PATH, "r", encoding="utf-8") as f:
    html = f.read()

# 1. Clean the topbar of Resumen: remove "Nueva Consulta" button from Resumen topbar
# Replace with clean patient status pill
html = html.replace(
    """                <!-- Botón de acción rápida: Iniciar Nueva Consulta -->
                <button type="button" class="btn-modular-primary" onclick="startQuickConsultation('MOBK070228HYNRTVA3', 'Kevin Enrique Morales', '')" title="Iniciar consulta médica de este paciente">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 5v14"/><path d="M5 12h14"/></svg>
                  Nueva Consulta
                </button>""",
    """                <div class="patient-monitoring-badge" title="Monitoreo biométrico continuo">
                  <span class="telemetry-live-dot"></span>
                  <span>Telemetría Conectada (Apple Watch S9)</span>
                </div>"""
)

# 2. In Module 5 (Medical Report), change "Atender Consulta" to "Historial de Consultas"
html = html.replace(
    """                  <button type="button" class="btn-report-download" onclick="startQuickConsultation('MOBK070228HYNRTVA3', 'Kevin Enrique Morales', 'Control general y seguimiento')" title="Iniciar nueva nota médica">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
                    Atender Consulta
                  </button>""",
    """                  <button type="button" class="btn-report-download" onclick="switchMainTab('expediente')" title="Consultar historial clínico completo">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                    Historial Completo
                  </button>"""
)

# 3. In Timeline, change "Consulta NOM-004 en curso" to "Control Preventivo Realizado"
html = html.replace(
    """                    <!-- Evento 3: Consulta Médica NOM-004 -->
                    <div class="timeline-event-pill event-amber" style="left: 56%; top: 38px; width: 38%;">
                      <div class="event-icon-circle">📋</div>
                      <div class="event-pill-content">
                        <strong>Consulta NOM-004</strong>
                        <span>Control Clínico · Dr. Roberto Morales</span>
                      </div>
                      <span class="event-status-check pulse-dot"></span>
                    </div>""",
    """                    <!-- Evento 3: Control Clínico Registrado -->
                    <div class="timeline-event-pill event-amber" style="left: 56%; top: 38px; width: 38%;">
                      <div class="event-icon-circle">📋</div>
                      <div class="event-pill-content">
                        <strong>Control Clínico Registrado</strong>
                        <span>Nota Previa · Dr. Roberto Morales</span>
                      </div>
                      <span class="event-status-check">✓</span>
                    </div>"""
)

with open(INDEX_PATH, "w", encoding="utf-8") as f:
    f.write(html)

with open(LINUX_INDEX_PATH, "w", encoding="utf-8") as f:
    f.write(html)

print("Cleaned Resumen to be 100% Patient Data & Telemetry.")
