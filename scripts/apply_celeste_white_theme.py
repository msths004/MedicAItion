# -*- coding: utf-8 -*-
"""
apply_celeste_white_theme.py
Transforms MedicAItion UI/UX into the fresh, friendly, minimalist "Blanco y Celeste" clinical style
inspired by the user's reference mockup (Med+ / Courtney Henry patient dashboard):
- Clean, airy white and soft celeste palette (#2589ff, #eaf3fe, #ffffff, #f4f7fb)
- Minimalist, simple, friendly white-and-celeste circular icon badges
- Tasteful italics in appropriate clinical contexts (subtitles, metadata, notes, status labels)
- Preserves 100% of the program's functions, views, tabs, and database logic.
"""

import os
import re

ROOTS = [
    r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion",
    r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion\Linux_Ver"
]

CELESTE_WHITE_THEME_CSS = """
/* ==========================================================================
   MINIMALIST WHITE & CELESTE FRIENDLY CLINICAL THEME (MED+ REFERENCE UI/UX)
   - Paleta Limpia, Aireada y Amigable: Blanco Puro, Celeste Cielo (#2589ff) y Pastel (#eaf3fe)
   - Simbolos Minimalistas, Simples, Blancos y Amigables con Contenedores Circulares
   - Cursivas Tasteful en Lugares Clnicos Correspondientes (Subttulos, Metadatos, Diagnsticos)
   - Funcionalidad y Estructura 100% Preservadas
   ========================================================================== */

@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,400;0,500;0,600;0,700;0,800;1,400;1,500;1,600;1,700&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* Variables Globales: Blanco & Celeste Fresco */
:root,
[data-theme="light"] {
  --bg-base: #f4f7fb !important;
  --bg-panel: #ffffff !important;
  --bg-card: #ffffff !important;
  --bg-input: #f8fafc !important;
  --bg-hover: #edf5fe !important;

  --border: #e2eaf2 !important;
  --border-accent: #cde0f1 !important;
  --border-focus: #2589ff !important;

  --text-primary: #1e293b !important;
  --text-secondary: #475569 !important;
  --text-muted: #8295a8 !important;

  /* Celeste Signature & Toques Degradados */
  --celeste-primary: #2589ff !important;
  --celeste-deep: #1b6fd1 !important;
  --celeste-soft: #eaf3fe !important;
  --celeste-subtle: #f0f7ff !important;
  --celeste-border: #c8e1fd !important;
  --celeste-gradient: linear-gradient(135deg, #2589ff 0%, #4facfe 100%) !important;
  --celeste-hero: linear-gradient(135deg, #2589ff 0%, #1e70d4 100%) !important;
  --celeste-card-grad: linear-gradient(180deg, #ffffff 0%, #f6faff 100%) !important;
  --celeste-silver: linear-gradient(135deg, #eaf3fe 0%, #f0f6ff 100%) !important;

  --shadow-friendly: 0 8px 24px -4px rgba(37, 137, 255, 0.08), 0 2px 6px -1px rgba(0, 0, 0, 0.02) !important;
  --shadow-card-hover: 0 14px 34px -4px rgba(37, 137, 255, 0.14), 0 4px 10px -2px rgba(0, 0, 0, 0.03) !important;
  --shadow-btn: 0 4px 14px rgba(37, 137, 255, 0.22) !important;
}

[data-theme="dark"] {
  --bg-base: #0b1326 !important;
  --bg-panel: #111c38 !important;
  --bg-card: #152244 !important;
  --bg-input: #1a2a52 !important;
  --bg-hover: #223563 !important;

  --border: #1f325e !important;
  --border-accent: #2e4a87 !important;
  --border-focus: #38bdf8 !important;

  --text-primary: #f8fafc !important;
  --text-secondary: #94a3b8 !important;
  --text-muted: #64748b !important;

  --celeste-primary: #38bdf8 !important;
  --celeste-deep: #0284c7 !important;
  --celeste-soft: #172a50 !important;
  --celeste-subtle: #132242 !important;
  --celeste-border: #25467e !important;
  --celeste-gradient: linear-gradient(135deg, #0284c7 0%, #38bdf8 100%) !important;
  --celeste-hero: linear-gradient(135deg, #0369a1 0%, #0284c7 100%) !important;
  --celeste-card-grad: linear-gradient(180deg, #152244 0%, #111c38 100%) !important;
  --celeste-silver: linear-gradient(135deg, #1a2d58 0%, #152345 100%) !important;

  --shadow-friendly: 0 8px 28px rgba(0, 0, 0, 0.45) !important;
  --shadow-card-hover: 0 16px 40px rgba(0, 0, 0, 0.6) !important;
  --shadow-btn: 0 4px 16px rgba(56, 189, 248, 0.2) !important;
}

/* Base Body: Sereno, Limpio y Aireado */
body {
  background: var(--bg-base) !important;
  color: var(--text-primary) !important;
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
}

/* ==========================================================================
   TIPOGRAFA: MODERNA, AMIGABLE Y CON CURSIVAS EN LUGARES CLNICOS
   ========================================================================== */

/* Encabezados y Ttulos Principales: Amigables, Limpios y con Carcter */
h1, h2, h3,
.modular-page-title,
.split-panel-title,
.card-section-title,
.patient-name-display,
.report-doc-title,
.patients-page-title,
.agenda-month-title,
.ecg-main-label {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-weight: 700 !important;
  color: var(--text-primary) !important;
  letter-spacing: -0.02em !important;
}

/* Cursivas Justas y Elegantes: Subttulos, Metadatos, Estados y Notas */
.modular-page-subtitle,
.split-panel-desc,
.patients-page-sub,
.ecg-last-checked,
.report-doc-meta,
.module-eyebrow,
.metric-card-label,
.meta-label,
.spec-label,
.picker-label,
.inspector-day-badge,
.report-doc-diagnosis,
.cal-legend-summary,
.ai-human-control,
.legal-enc-sub {
  font-style: italic !important;
  color: var(--text-muted) !important;
  letter-spacing: 0.01em !important;
}

/* Cifras de Signos Vitales y Mtricas: Rectas y de Mxima Precisin */
.spec-val,
.bpm-num,
.stat-val,
.metric-card-val,
.vital-stat-value,
.stat-number {
  font-style: normal !important;
  font-weight: 700 !important;
  font-variant-numeric: tabular-nums !important;
  color: var(--text-primary) !important;
}

/* ==========================================================================
   SMBOLOS MINIMALISTAS & AMIGABLES (CIRCULARES, BLANCOS Y CELESTES)
   ========================================================================== */

/* Contenedores Circulares Minimalistas para conos */
.vital-stat-icon,
.event-icon-circle,
.spec-icon-badge,
.module-icon-circle,
.card-icon-round {
  width: 36px !important;
  height: 36px !important;
  min-width: 36px !important;
  border-radius: 50% !important;
  background: var(--celeste-soft) !important;
  color: var(--celeste-primary) !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
  border: 1px solid var(--celeste-border) !important;
  transition: all 0.2s ease !important;
}

/* Variacin con cono Blanco sobre Fondo Celeste Slido */
.icon-badge-celeste-solid,
.vital-stat-tile.is-highlight .vital-stat-icon,
.ecg-check-icon {
  background: var(--celeste-hero) !important;
  color: #ffffff !important;
  border: none !important;
  box-shadow: 0 4px 12px rgba(37, 137, 255, 0.28) !important;
}

/* ==========================================================================
   SIDEBAR AMIGABLE & MINIMALISTA
   ========================================================================== */
.sidebar {
  background: var(--bg-panel) !important;
  border-right: 1px solid var(--border) !important;
}

.brand-title {
  color: var(--text-primary) !important;
  font-weight: 800 !important;
}

.brand-title .ai-brand-accent {
  color: var(--celeste-primary) !important;
}

.brand-subtitle {
  color: var(--text-muted) !important;
  font-style: italic !important;
  letter-spacing: 0.04em !important;
}

.nav-section-label {
  color: var(--text-muted) !important;
  font-style: italic !important;
  font-weight: 600 !important;
  font-size: 11px !important;
  letter-spacing: 0.06em !important;
}

/* Botones de Navegacin Lateral */
.sidebar-nav-btn {
  background: transparent !important;
  color: var(--text-secondary) !important;
  border-radius: 12px !important;
  border: 1px solid transparent !important;
  margin: 3px 0 !important;
  padding: 10px 14px !important;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
}

.sidebar-nav-btn svg {
  color: var(--text-muted) !important;
  transition: color 0.2s ease, transform 0.2s ease !important;
}

.sidebar-nav-btn:hover {
  background: var(--bg-hover) !important;
  color: var(--celeste-primary) !important;
}

.sidebar-nav-btn:hover svg {
  color: var(--celeste-primary) !important;
  transform: scale(1.08) !important;
}

/* PESTAA ACTIVA: Celeste Fresco y Amigable */
.sidebar-nav-btn.active {
  background: var(--celeste-soft) !important;
  color: var(--celeste-primary) !important;
  border: 1px solid var(--celeste-border) !important;
  border-left: 4px solid var(--celeste-primary) !important;
  box-shadow: 0 4px 16px rgba(37, 137, 255, 0.12) !important;
  transform: translateX(2px) !important;
}

.sidebar-nav-btn.active svg {
  color: var(--celeste-primary) !important;
  stroke-width: 2.3px !important;
}

.sidebar-nav-btn.active span {
  font-weight: 700 !important;
}

/* ==========================================================================
   TOPBAR: BLANCA, MINIMALISTA Y ELEGANTE
   ========================================================================== */
.topbar {
  background: var(--bg-panel) !important;
  border-bottom: 1px solid var(--border) !important;
}

/* Barra de bsqueda estilo Med+ */
.topbar-search-wrap,
.search-box {
  background: var(--bg-input) !important;
  border: 1.5px solid var(--border) !important;
  border-radius: 999px !important;
  transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}

.topbar-search-wrap:focus-within,
.search-box:focus-within {
  border-color: var(--celeste-primary) !important;
  box-shadow: 0 0 0 3px var(--celeste-glow) !important;
}

.topbar-search-input {
  color: var(--text-primary) !important;
  font-size: 13.5px !important;
}

.topbar-search-input::placeholder {
  color: var(--text-muted) !important;
  font-style: italic !important;
}

/* Botn Cambiador de Tema: Celeste Suave */
.topbar-theme-pill {
  background: var(--celeste-soft) !important;
  border: 1.5px solid var(--celeste-border) !important;
  color: var(--celeste-primary) !important;
  font-style: italic !important;
  font-weight: 600 !important;
  border-radius: 999px !important;
}

.topbar-theme-pill:hover {
  background: #ddecfa !important;
  box-shadow: 0 2px 10px rgba(37, 137, 255, 0.18) !important;
}

/* ==========================================================================
   TARJETAS MODULARES & HERO BENTO (MED+ ESTILO BLANCO Y CELESTE)
   ========================================================================== */
.modular-card,
.vital-stat-tile,
.consultation-card,
.metric-card,
.timeline-card,
.reports-kpi-card {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 20px !important;
  box-shadow: var(--shadow-friendly) !important;
  transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease !important;
}

.modular-card:hover {
  border-color: var(--border-accent) !important;
  box-shadow: var(--shadow-card-hover) !important;
  transform: translateY(-2px) !important;
}

/* Selector de Paciente en Topbar Strip */
.modular-patient-picker {
  background: var(--bg-panel) !important;
  border: 1.5px solid var(--celeste-border) !important;
  border-radius: 999px !important;
  box-shadow: 0 2px 8px rgba(37, 137, 255, 0.08) !important;
}

.patient-monitoring-badge {
  background: var(--celeste-soft) !important;
  border: 1px solid var(--celeste-border) !important;
  color: var(--celeste-deep) !important;
  border-radius: 999px !important;
  font-style: italic !important;
}

.telemetry-live-dot {
  background: #10b981 !important;
  box-shadow: 0 0 8px #10b981 !important;
}

/* Tarjeta Perfil Paciente */
.patient-hero-card {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
}

.patient-name-display {
  font-size: 22px !important;
  font-weight: 700 !important;
  color: var(--text-primary) !important;
}

.patient-avatar-large {
  background: var(--celeste-hero) !important;
  color: #ffffff !important;
  font-weight: 700 !important;
  border: 3px solid #ffffff !important;
  box-shadow: 0 6px 18px rgba(37, 137, 255, 0.28) !important;
}

/* Pastilla de Alergia: Fondo suave, alerta clnica sobria */
.patient-allergies-chip-bar .allergy-tag {
  background: #fff1f2 !important;
  color: #e11d48 !important;
  border: 1px solid #fecdd3 !important;
  font-style: italic !important;
  font-size: 11.5px !important;
  padding: 5px 12px !important;
  border-radius: 999px !important;
}

/* Tarjeta de Telemetra Cardaca ECG */
.ecg-live-card {
  background: var(--celeste-card-grad) !important;
  border: 1px solid var(--celeste-border) !important;
}

.ecg-title-badge .ecg-check-icon {
  background: var(--celeste-hero) !important;
  color: #ffffff !important;
  border-radius: 50% !important;
  width: 28px !important;
  height: 28px !important;
  display: inline-flex !important;
  align-items: center !important;
  justify-content: center !important;
}

.ecg-bpm-giant .bpm-num {
  font-size: 44px !important;
  font-weight: 800 !important;
  color: var(--celeste-primary) !important;
}

.ecg-bpm-giant .bpm-unit {
  font-style: italic !important;
  color: var(--text-muted) !important;
}

/* Barras del Grfico ECG en Celeste Fresco con degradado */
.ecg-bar {
  background: linear-gradient(180deg, #2589ff 0%, #a0cbf9 100%) !important;
  border-radius: 6px !important;
  opacity: 0.9 !important;
}

/* FILA DE BENTO METRICS: Tarjeta Destacada Celeste Estilo Med+ ("Sleep 7h 33m") */
.modular-grid-row.row-metrics .modular-card:first-child {
  background: var(--celeste-hero) !important;
  color: #ffffff !important;
  border: none !important;
  box-shadow: 0 10px 28px rgba(37, 137, 255, 0.3) !important;
}

.modular-grid-row.row-metrics .modular-card:first-child .metric-card-label,
.modular-grid-row.row-metrics .modular-card:first-child .metric-card-val,
.modular-grid-row.row-metrics .modular-card:first-child .metric-card-change {
  color: #ffffff !important;
}

.modular-grid-row.row-metrics .modular-card:first-child .metric-prog-track {
  background: rgba(255, 255, 255, 0.28) !important;
}

.modular-grid-row.row-metrics .modular-card:first-child .metric-prog-fill {
  background: #ffffff !important;
}

/* Barras de Progreso Generales: Celeste Elegante */
.metric-prog-track,
.stat-progress-bar {
  background: #edf3fa !important;
  border: 1px solid var(--border) !important;
  border-radius: 999px !important;
  overflow: hidden !important;
}

.metric-prog-fill.fill-blue,
.stat-progress-bar > div:nth-child(1) {
  background: linear-gradient(90deg, #2589ff 0%, #56ccf2 100%) !important;
}

.metric-prog-fill.fill-amber,
.stat-progress-bar > div:nth-child(2) {
  background: linear-gradient(90deg, #f59e0b 0%, #fbbf24 100%) !important;
}

.metric-prog-fill.fill-green,
.stat-progress-bar > div:nth-child(3) {
  background: linear-gradient(90deg, #10b981 0%, #34d399 100%) !important;
}

.metric-prog-fill.fill-purple {
  background: linear-gradient(90deg, #8b5cf6 0%, #c084fc 100%) !important;
}

/* Tarjeta de Reporte Mdico */
.medical-report-card {
  background: var(--bg-card) !important;
}

.report-illustration-badge .doc-icon-3d {
  background: var(--celeste-soft) !important;
  border-radius: 50% !important;
  padding: 12px !important;
  border: 1.5px solid var(--celeste-border) !important;
}

.btn-report-view {
  background: var(--celeste-soft) !important;
  color: var(--celeste-primary) !important;
  border: 1.5px solid var(--celeste-border) !important;
  font-weight: 600 !important;
  border-radius: 999px !important;
}

.btn-report-view:hover {
  background: #ddecfa !important;
}

.btn-report-download {
  background: var(--celeste-hero) !important;
  color: #ffffff !important;
  border: none !important;
  font-weight: 600 !important;
  border-radius: 999px !important;
  box-shadow: var(--shadow-btn) !important;
}

.btn-report-download:hover {
  opacity: 0.94 !important;
  transform: translateY(-1px) !important;
}

/* Timeline: Eventos con conos circulares celestes y blancos */
.timeline-event-pill {
  background: var(--bg-card) !important;
  border: 1.5px solid var(--celeste-border) !important;
  border-radius: 999px !important;
  box-shadow: var(--shadow-friendly) !important;
}

.timeline-event-pill .event-icon-circle {
  background: var(--celeste-primary) !important;
  color: #ffffff !important;
  border-radius: 50% !important;
}

.timeline-event-pill strong {
  color: var(--text-primary) !important;
}

.timeline-event-pill span {
  font-style: italic !important;
  color: var(--text-muted) !important;
}

/* ==========================================================================
   NUEVA CONSULTA - WORKSTATION BLANCO & CELESTE (2 COLUMNAS)
   ========================================================================== */
#consulta-layout {
  display: grid !important;
  grid-template-columns: 360px minmax(0, 1fr) !important;
  gap: 24px !important;
}

.clinical-split-panel {
  background: var(--bg-panel) !important;
  border: 1px solid var(--border) !important;
  border-radius: 20px !important;
  box-shadow: var(--shadow-friendly) !important;
}

/* Botones de Selector de Mtodo (Audio / Texto / Transcripcin) */
.capture-mode-btn,
.mode-switch-btn,
.tab-pill {
  background: var(--bg-input) !important;
  color: var(--text-secondary) !important;
  border: 1px solid var(--border) !important;
  border-radius: 999px !important;
  font-weight: 600 !important;
  padding: 8px 18px !important;
  transition: all 0.2s ease !important;
}

.capture-mode-btn.active,
.mode-switch-btn.active,
.tab-pill.active {
  background: var(--celeste-hero) !important;
  color: #ffffff !important;
  border-color: var(--celeste-primary) !important;
  box-shadow: 0 4px 14px rgba(37, 137, 255, 0.28) !important;
}

.capture-mode-btn.active svg,
.mode-switch-btn.active svg {
  color: #ffffff !important;
}

/* Plantillas Rpidas: Pastillas Celestes Suaves */
.quick-template-chip,
.template-pill-btn {
  background: var(--celeste-soft) !important;
  color: var(--celeste-deep) !important;
  border: 1px solid var(--celeste-border) !important;
  font-style: italic !important;
  border-radius: 999px !important;
  padding: 6px 14px !important;
}

.quick-template-chip:hover,
.template-pill-btn:hover {
  background: var(--celeste-hero) !important;
  color: #ffffff !important;
  border-color: var(--celeste-primary) !important;
}

/* Botones de Accin Clnica Principales (Guardar Consulta, Nuevo Registro) */
.btn-primary-action,
.btn-save-note,
.btn-dark-pill,
.btn-register-patient-modern {
  background: var(--celeste-hero) !important;
  color: #ffffff !important;
  border: none !important;
  border-radius: 999px !important;
  font-weight: 600 !important;
  box-shadow: var(--shadow-btn) !important;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
}

.btn-primary-action:hover,
.btn-save-note:hover,
.btn-dark-pill:hover,
.btn-register-patient-modern:hover {
  opacity: 0.94 !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 6px 20px rgba(37, 137, 255, 0.32) !important;
}

/* ==========================================================================
   DR. OSO FLOTANTE & CHAT EN BLANCO Y CELESTE AMIGABLE
   ========================================================================== */

/* Botn Flotante FAB: Blanco con Borde Celeste Radiante */
.pulso-fab-btn {
  background: #ffffff !important;
  border: 2.5px solid var(--celeste-primary) !important;
  box-shadow: 0 10px 28px rgba(37, 137, 255, 0.25), 0 0 14px rgba(56, 189, 248, 0.2) !important;
}

/* Panel de Chat de Dr. Oso */
.pulso-chat-panel {
  background: var(--bg-panel) !important;
  border: 2px solid var(--celeste-border) !important;
  box-shadow: 0 20px 50px rgba(37, 137, 255, 0.18) !important;
  border-radius: 22px !important;
}

.pulso-chat-header {
  background: var(--celeste-hero) !important;
  border-bottom: 2px solid var(--celeste-deep) !important;
  color: #ffffff !important;
}

.pulso-chat-title {
  color: #ffffff !important;
  font-weight: 700 !important;
}

.pulso-chat-subtitle {
  color: rgba(255, 255, 255, 0.85) !important;
  font-style: italic !important;
}

/* Burbujas de Chat: Blanco y Celeste */
.pulso-msg-user .pulso-msg-bubble {
  background: var(--celeste-hero) !important;
  color: #ffffff !important;
  border-radius: 16px 16px 2px 16px !important;
  box-shadow: 0 4px 12px rgba(37, 137, 255, 0.2) !important;
}

.pulso-msg-assistant .pulso-msg-bubble {
  background: #ffffff !important;
  color: var(--text-primary) !important;
  border: 1.5px solid var(--border) !important;
  border-radius: 16px 16px 16px 2px !important;
  box-shadow: var(--shadow-friendly) !important;
}

.pulso-chat-footer {
  background: var(--bg-panel) !important;
  border-top: 1px solid var(--border) !important;
}

.pulso-chat-input {
  background: var(--bg-input) !important;
  color: var(--text-primary) !important;
  border: 1.5px solid var(--border) !important;
  border-radius: 12px !important;
}

.pulso-chat-input:focus {
  border-color: var(--celeste-primary) !important;
  box-shadow: 0 0 0 3px var(--celeste-glow) !important;
}

.pulso-send-btn {
  background: var(--celeste-hero) !important;
  color: #ffffff !important;
  border-radius: 12px !important;
  box-shadow: var(--shadow-btn) !important;
}

/* Indicador de Escritura de Dr. Oso */
.pulso-typing-indicator {
  color: var(--celeste-primary) !important;
  font-style: italic !important;
}

.pulso-typing-indicator .dot {
  background-color: var(--celeste-primary) !important;
}

/* ==========================================================================
   AGENDA / CITAS & DIRECTORIO DE PACIENTES
   ========================================================================== */
.cal-legend-bar {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 14px !important;
}

.patient-table th {
  color: var(--text-muted) !important;
  font-style: italic !important;
  border-bottom: 2px solid var(--border) !important;
}

.patient-table td strong {
  color: var(--text-primary) !important;
  font-weight: 700 !important;
}

.patient-row:hover {
  background: var(--celeste-soft) !important;
}
"""

def update_css(base_dir):
    p = os.path.join(base_dir, "frontend", "style.css")
    if not os.path.exists(p):
        return
    with open(p, "r", encoding="utf-8") as f:
        content = f.read()

    # Locate previous B&W theme marker or Celeste theme marker
    bw_marker = "/* ==========================================================================\n   FORMAL ELEGANT BLACK & WHITE EDITORIAL CLINICAL THEME"
    celeste_marker = "/* ==========================================================================\n   MINIMALIST WHITE & CELESTE FRIENDLY CLINICAL THEME"

    if bw_marker in content:
        idx = content.find(bw_marker)
        content = content[:idx] + CELESTE_WHITE_THEME_CSS.strip() + "\n"
    elif celeste_marker in content:
        idx = content.find(celeste_marker)
        content = content[:idx] + CELESTE_WHITE_THEME_CSS.strip() + "\n"
    else:
        content = content + "\n\n" + CELESTE_WHITE_THEME_CSS.strip() + "\n"

    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Applied Celeste & White Theme to {p}")

for root in ROOTS:
    update_css(root)

print("Minimalist White & Celeste theme successfully applied.")
