# -*- coding: utf-8 -*-
"""
rebuild_modular_dashboard.py
Rebuilds the Resumen (Dashboard) into the clean, spacious Modular Patient Dashboard
inspired 1:1 by media_1794700216734_e9ed90ad.jpg and frame_50.jpg,
and refines Nueva Consulta into a spacious, modular workstation with breathing room.
"""
import os
import re

BASE_DIR = r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion"
INDEX_PATH = os.path.join(BASE_DIR, "frontend", "index.html")
STYLE_PATH = os.path.join(BASE_DIR, "frontend", "style.css")
APP_PATH = os.path.join(BASE_DIR, "frontend", "app.js")

LINUX_INDEX_PATH = os.path.join(BASE_DIR, "Linux_Ver", "frontend", "index.html")
LINUX_STYLE_PATH = os.path.join(BASE_DIR, "Linux_Ver", "frontend", "style.css")
LINUX_APP_PATH = os.path.join(BASE_DIR, "Linux_Ver", "frontend", "app.js")

with open(INDEX_PATH, "r", encoding="utf-8") as f:
    html = f.read()

# ----------------------------------------------------------------------
# 1. REBUILD PANEL-DASHBOARD-SECTION (RESUMEN)
# ----------------------------------------------------------------------
dash_start = '<section class="view-panel" id="panel-dashboard-section">'
dash_end = '</section>\n\n        <!-- =================================================================\n             VIEW: REPORTES Y ESTADÍSTICAS'
if dash_end not in html:
    dash_end = '</section>\r\n\r\n        <!-- =================================================================\r\n             VIEW: REPORTES Y ESTADÍSTICAS'

idx_d_start = html.find(dash_start)
idx_d_end = html.find(dash_end, idx_d_start)

if idx_d_start != -1 and idx_d_end != -1:
    modular_dashboard_html = """<section class="view-panel" id="panel-dashboard-section">
          <!-- =================================================================
               MODULAR CLINICAL DASHBOARD (PATIENT PROFILE & TELEMETRY COMMAND)
               Inspirado 1:1 en la arquitectura modular de las referencias clínicas
               ================================================================= -->
          <div class="modular-dashboard-wrapper">

            <!-- BARRA DE CONTROL MODULAR SUPERIOR -->
            <div class="modular-topbar-strip">
              <div class="modular-topbar-left">
                <h1 class="modular-page-title">Perfil Clínico & Resumen de Paciente</h1>
                <span class="modular-page-subtitle">Sincronización biométrica en tiempo real · NOM-004 / NOM-024</span>
              </div>

              <div class="modular-topbar-actions">
                <!-- Selector rápido de paciente -->
                <div class="modular-patient-picker" title="Seleccionar paciente activo">
                  <span class="picker-label">PACIENTE:</span>
                  <select id="dashboard-patient-select" class="modular-select-pill" onchange="onDashboardPatientChange(this.value)">
                    <option value="MOBK070228HYNRTVA3">Kevin Enrique Morales B. (19 años)</option>
                    <option value="GOPC790814HYNCLN04">Carlos Manuel González P. (47 años)</option>
                    <option value="TESTCURP1234567890">Juan Pérez Gómez (45 años)</option>
                  </select>
                </div>

                <!-- Botón de acción rápida: Iniciar Nueva Consulta -->
                <button type="button" class="btn-modular-primary" onclick="startQuickConsultation('MOBK070228HYNRTVA3', 'Kevin Enrique Morales', '')" title="Iniciar consulta médica de este paciente">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 5v14"/><path d="M5 12h14"/></svg>
                  Nueva Consulta
                </button>
              </div>
            </div>

            <!-- FILA 1: PERFIL DEL PACIENTE + ECG / TELEMETRÍA CARDÍACA EN VIVO -->
            <div class="modular-grid-row row-hero">

              <!-- MÓDULO 1: TARJETA DE IDENTIDAD DEL PACIENTE (PATIENT CARD) -->
              <div class="modular-card patient-hero-card">
                <div class="patient-card-header">
                  <span class="module-eyebrow">DATOS DEMOGRÁFICOS</span>
                  <div class="patient-card-options-btn" title="Opciones de expediente">•••</div>
                </div>

                <div class="patient-hero-body">
                  <div class="patient-photo-container">
                    <div class="patient-avatar-large" id="dash-patient-avatar">KM</div>
                    <div class="patient-status-indicator-dot online" title="Paciente activo en clínica"></div>
                  </div>

                  <div class="patient-hero-details">
                    <h2 class="patient-name-display" id="dash-patient-name">Kevin Enrique Morales Bautista</h2>
                    
                    <div class="patient-specs-grid">
                      <div class="spec-item">
                        <span class="spec-label">Edad</span>
                        <strong class="spec-val" id="dash-patient-age">19 Años</strong>
                      </div>
                      <div class="spec-item">
                        <span class="spec-label">Nacimiento</span>
                        <strong class="spec-val" id="dash-patient-dob">28/02/2007</strong>
                      </div>
                      <div class="spec-item">
                        <span class="spec-label">ID Clínico</span>
                        <strong class="spec-val" id="dash-patient-id">PT-2026-0001</strong>
                      </div>
                      <div class="spec-item">
                        <span class="spec-label">Sexo</span>
                        <strong class="spec-val" id="dash-patient-gender">Masculino</strong>
                      </div>
                      <div class="spec-item">
                        <span class="spec-label">Grupo Sanguíneo</span>
                        <strong class="spec-val blood-highlight" id="dash-patient-blood">A+ (Rh+)</strong>
                      </div>
                      <div class="spec-item">
                        <span class="spec-label">Teléfono</span>
                        <strong class="spec-val" id="dash-patient-phone">+52 999 415 6931</strong>
                      </div>
                    </div>

                    <!-- Alergias Destacadas del Paciente -->
                    <div class="patient-allergies-chip-bar" id="dash-patient-allergies">
                      <span class="allergy-tag">⚠️ Alergia Crítica: Penicilina, AINEs (Ketorolaco)</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- MÓDULO 2: ECG & TELEMETRÍA EN VIVO (CARDIO TELEMETRY) -->
              <div class="modular-card ecg-live-card">
                <div class="ecg-card-header">
                  <div class="ecg-title-badge">
                    <span class="ecg-check-icon">✓</span>
                    <div>
                      <div class="ecg-main-label">ECG Ritmo Sinusal</div>
                      <span class="ecg-last-checked">Sincronizado hoy, 10:45 AM</span>
                    </div>
                  </div>
                  <div class="ecg-header-options">•••</div>
                </div>

                <div class="ecg-telemetry-meta-bar">
                  <div class="ecg-meta-col">
                    <span class="meta-label">⏱️ Duración</span>
                    <strong class="meta-val">1m 30s</strong>
                  </div>
                  <div class="ecg-meta-col">
                    <span class="meta-label">🩺 Estado</span>
                    <strong class="meta-val status-normal">Normal</strong>
                  </div>
                  <div class="ecg-meta-col">
                    <span class="meta-label">⌚ Dispositivo</span>
                    <strong class="meta-val" id="dash-device-name">Apple Watch S9</strong>
                  </div>
                  <div class="ecg-bpm-giant">
                    <span class="bpm-num" id="dash-bpm-value">82</span>
                    <span class="bpm-unit">bpm</span>
                  </div>
                </div>

                <!-- Gráfica Digital de Barras y Onda Cardíaca de Alta Definición -->
                <div class="ecg-digital-graph-wrap">
                  <div class="ecg-bars-equalizer">
                    <span style="height: 38%"></span>
                    <span style="height: 65%"></span>
                    <span style="height: 48%"></span>
                    <span style="height: 82%"></span>
                    <span style="height: 40%"></span>
                    <span style="height: 60%"></span>
                    <span style="height: 95%"></span>
                    <span style="height: 52%"></span>
                    <span style="height: 70%"></span>
                    <span style="height: 42%"></span>
                    <span style="height: 88%"></span>
                    <span style="height: 58%"></span>
                    <span style="height: 64%"></span>
                    <span style="height: 36%"></span>
                    <span style="height: 78%"></span>
                    <span style="height: 46%"></span>
                    <span style="height: 92%"></span>
                    <span style="height: 62%"></span>
                    <span style="height: 50%"></span>
                    <span style="height: 74%"></span>
                    <span style="height: 38%"></span>
                    <span style="height: 80%"></span>
                    <span style="height: 44%"></span>
                    <span style="height: 66%"></span>
                  </div>
                  <svg class="ecg-line-overlay" viewBox="0 0 500 50" preserveAspectRatio="none">
                    <path d="M0,25 L80,25 L90,10 L100,42 L110,4 L120,44 L130,25 L240,25 L250,10 L260,42 L270,4 L280,44 L290,25 L400,25 L410,10 L420,42 L430,4 L440,44 L450,25 L500,25" fill="none" stroke="var(--blue-accent)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
                  </svg>
                </div>
              </div>

            </div>

            <!-- FILA 2: 4 MÉTRICAS CLÍNICAS MODULARES EN HORIZONTAL -->
            <div class="modular-metrics-row">
              <!-- KPI 1: Health Overview -->
              <div class="modular-card kpi-metric-card">
                <div class="kpi-metric-head">
                  <span class="kpi-metric-name">Índice de Salud General</span>
                  <span class="kpi-dots">•••</span>
                </div>
                <div class="kpi-metric-val-row">
                  <strong class="kpi-metric-number">84%</strong>
                  <span class="kpi-delta-pill delta-up">+3.1%</span>
                </div>
                <div class="kpi-progress-track">
                  <div class="kpi-progress-bar bar-blue" style="width: 84%"></div>
                </div>
                <div class="kpi-sub-text">Constantes vitales en rango óptimo</div>
              </div>

              <!-- KPI 2: Recovery Status -->
              <div class="modular-card kpi-metric-card">
                <div class="kpi-metric-head">
                  <span class="kpi-metric-name">Estado de Recuperación</span>
                  <span class="kpi-dots">•••</span>
                </div>
                <div class="kpi-metric-val-row">
                  <strong class="kpi-metric-number">91%</strong>
                  <span class="kpi-delta-pill delta-up">+4.2%</span>
                </div>
                <div class="kpi-progress-track">
                  <div class="kpi-progress-bar bar-amber" style="width: 91%"></div>
                </div>
                <div class="kpi-sub-text">Excelente evolución post-tratamiento</div>
              </div>

              <!-- KPI 3: Medication Tracking -->
              <div class="modular-card kpi-metric-card">
                <div class="kpi-metric-head">
                  <span class="kpi-metric-name">Adherencia Terapéutica</span>
                  <span class="kpi-dots">•••</span>
                </div>
                <div class="kpi-metric-val-row">
                  <strong class="kpi-metric-number">58%</strong>
                  <span class="kpi-delta-pill delta-down">-3.1%</span>
                </div>
                <div class="kpi-progress-track">
                  <div class="kpi-progress-bar bar-lime" style="width: 58%"></div>
                </div>
                <div class="kpi-sub-text">Recordatorio de toma activado</div>
              </div>

              <!-- KPI 4: Biometric Step Tracker -->
              <div class="modular-card kpi-metric-card kpi-gauge-card">
                <div class="kpi-metric-head">
                  <span class="kpi-metric-name">Monitoreo Biométrico</span>
                  <span class="kpi-dots">•••</span>
                </div>
                <div class="kpi-metric-val-row">
                  <strong class="kpi-metric-number">7,520</strong>
                  <span class="kpi-metric-total">/ 8,000 pasos</span>
                </div>
                <div class="kpi-progress-track">
                  <div class="kpi-progress-bar bar-purple" style="width: 94%"></div>
                </div>
                <div class="kpi-sub-text">Meta diaria al 94% completada</div>
              </div>
            </div>

            <!-- FILA 3: CRONOGRAMA DE ACTIVIDAD + REPORTE MÉDICO NOM-004 -->
            <div class="modular-grid-row row-bottom">

              <!-- MÓDULO 4: LÍNEA DE TIEMPO CLÍNICA Y ACTIVIDAD (TIMELINE TRACKING) -->
              <div class="modular-card timeline-tracking-card">
                <div class="card-section-header">
                  <div>
                    <h3 class="card-section-title">Cronograma de Actividad & Consultas</h3>
                    <span class="card-section-sub">Eventos clínicos y sincronizaciones del día de hoy</span>
                  </div>
                  <div class="header-dots">•••</div>
                </div>

                <div class="timeline-visual-container">
                  <!-- Escala de Horas -->
                  <div class="timeline-hours-axis">
                    <div class="hour-mark"><span>08:00 AM</span></div>
                    <div class="hour-mark"><span>10:00 AM</span></div>
                    <div class="hour-mark"><span>12:00 PM</span></div>
                    <div class="hour-mark"><span>02:00 PM</span></div>
                    <div class="hour-mark"><span>04:00 PM</span></div>
                    <div class="hour-mark"><span>06:00 PM</span></div>
                  </div>

                  <!-- Cuadrícula de Eventos Horarios con Líneas Punteadas -->
                  <div class="timeline-slots-grid">
                    <div class="timeline-guide-line" style="left: 0%"></div>
                    <div class="timeline-guide-line" style="left: 20%"></div>
                    <div class="timeline-guide-line" style="left: 40%"></div>
                    <div class="timeline-guide-line" style="left: 60%"></div>
                    <div class="timeline-guide-line" style="left: 80%"></div>
                    <div class="timeline-guide-line" style="left: 100%"></div>

                    <!-- Evento 1: Triaje matutino -->
                    <div class="timeline-event-pill event-cyan" style="left: 2%; top: 12px; width: 34%;">
                      <div class="event-icon-circle">🚶</div>
                      <div class="event-pill-content">
                        <strong>Actividad Matutina</strong>
                        <span>7,170 Pasos · 08:00 - 08:45 AM</span>
                      </div>
                      <span class="event-status-check">✓</span>
                    </div>

                    <!-- Evento 2: Toma de Signos Vitales -->
                    <div class="timeline-event-pill event-green" style="left: 22%; top: 76px; width: 35%;">
                      <div class="event-icon-circle">🩺</div>
                      <div class="event-pill-content">
                        <strong>Triaje / Signos Vitales</strong>
                        <span>TA 120/78 · FC 82 · 10:15 AM</span>
                      </div>
                      <span class="event-status-check">✓</span>
                    </div>

                    <!-- Evento 3: Consulta Médica NOM-004 -->
                    <div class="timeline-event-pill event-amber" style="left: 56%; top: 38px; width: 38%;">
                      <div class="event-icon-circle">📋</div>
                      <div class="event-pill-content">
                        <strong>Consulta NOM-004</strong>
                        <span>Control Clínico · Dr. Roberto Morales</span>
                      </div>
                      <span class="event-status-check pulse-dot"></span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- MÓDULO 5: REPORTE MÉDICO NOM-004 & ÚLTIMA CONSULTA (MEDICAL REPORT) -->
              <div class="modular-card medical-report-card">
                <div class="card-section-header">
                  <h3 class="card-section-title">Último Reporte Médico</h3>
                  <div class="header-dots">•••</div>
                </div>

                <div class="report-card-center-preview">
                  <div class="report-illustration-badge">
                    <div class="doc-icon-3d">
                      <svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="#0284c7" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
                    </div>
                  </div>

                  <h4 class="report-doc-title">Consulta de Control General NOM-004</h4>
                  <div class="report-doc-meta">
                    <span class="report-calendar-icon">📅</span>
                    <span>14 Nov 2026 · Dr. Roberto Morales (YUC-CR-001)</span>
                  </div>
                  <p class="report-doc-diagnosis">
                    <strong>Dx CIE-10:</strong> J00 Rinofaringitis Aguda · Cuadro leve controlado.
                  </p>
                </div>

                <!-- Botones de Acción de 1 Clic (View Report & Download) -->
                <div class="report-card-actions">
                  <button type="button" class="btn-report-view" onclick="openPatientProfile('MOBK070228HYNRTVA3')" title="Ver expediente y nota completa">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/></svg>
                    Ver Expediente
                  </button>
                  <button type="button" class="btn-report-download" onclick="startQuickConsultation('MOBK070228HYNRTVA3', 'Kevin Enrique Morales', 'Control general y seguimiento')" title="Iniciar nueva nota médica">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 11 12 14 22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
                    Atender Consulta
                  </button>
                </div>
              </div>

            </div>

            <!-- SLOTS AUXILIARES OCULTOS PARA COMPATIBILIDAD CON SCRIPTS JS DE KPIS -->
            <div style="display:none;" aria-hidden="true">
              <span id="kpi-pendientes">3</span>
              <span id="kpi-sala">1</span>
              <span id="kpi-criticos">0</span>
              <span id="kpi-atendidas">8</span>
              <div id="next-patient-body"></div>
              <div id="dashboard-agenda-list"></div>
              <div id="dashboard-consultas-list"></div>
              <div id="dashboard-tasks-list"></div>
              <div id="epi-mini-list"></div>
            </div>

          </div>
        </section>"""
    html = html[:idx_d_start] + modular_dashboard_html + html[idx_d_end:]
    print("Replaced panel-dashboard-section with Modular Patient Dashboard.")
else:
    print(f"Could not find dashboard markers: start={idx_d_start}, end={idx_d_end}")

with open(INDEX_PATH, "w", encoding="utf-8") as f:
    f.write(html)

with open(LINUX_INDEX_PATH, "w", encoding="utf-8") as f:
    f.write(html)

print("Saved updated index.html successfully.")
