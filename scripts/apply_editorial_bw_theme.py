# -*- coding: utf-8 -*-
"""
apply_editorial_bw_theme.py
Transforms MedicAItion into a Formal, Elegant, Black & White Editorial Clinical UI
with tasteful italic typography (without overdoing it) and subtle luxury gradients.
Maintains all program structures, views, tabs, and functionality 100% intact.
"""

import os
import re

ROOTS = [
    r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion",
    r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion\Linux_Ver"
]

BW_THEME_CSS = """
/* ==========================================================================
   FORMAL ELEGANT BLACK & WHITE EDITORIAL CLINICAL THEME
   - Paleta Monocromtica Formal de Alta Gama (Black, White, Charcoal, Silver)
   - Tipografa Editorial con Predominancia de Cursivas Clnicas Elegantes
   - Toques Sutiles de Degradados Perlados, Metlicos y Obsidianos
   ========================================================================== */

@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,500;0,600;0,700;1,400;1,500;1,600;1,700&family=Plus+Jakarta+Sans:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500;1,600&display=swap');

/* Redefinicin de Variables Globales a Blanco y Negro Editorial */
:root,
[data-theme="light"] {
  --bg-base: #f9f9fb !important;
  --bg-panel: #ffffff !important;
  --bg-card: #ffffff !important;
  --bg-input: #f4f4f6 !important;
  --bg-hover: #ebebee !important;
  --border: #e4e4e7 !important;
  --border-accent: #d4d4d8 !important;
  --border-focus: #09090b !important;
  --text-primary: #09090b !important;
  --text-secondary: #3f3f46 !important;
  --text-muted: #71717a !important;

  /* Degradados Sutiles B&W */
  --grad-hero: linear-gradient(135deg, #18181b 0%, #09090b 100%) !important;
  --grad-card: linear-gradient(180deg, #ffffff 0%, #fbfbfc 100%) !important;
  --grad-card-raised: linear-gradient(145deg, #ffffff 0%, #f4f4f7 100%) !important;
  --grad-pearl: linear-gradient(145deg, #ffffff 0%, #f5f5f7 100%) !important;
  --grad-silver: linear-gradient(135deg, #f4f4f5 0%, #e4e4e7 100%) !important;
  --grad-dark-btn: linear-gradient(135deg, #09090b 0%, #27272a 100%) !important;
  --grad-bar-dark: linear-gradient(90deg, #09090b 0%, #52525b 100%) !important;
  --grad-bar-mid: linear-gradient(90deg, #27272a 0%, #71717a 100%) !important;
  --grad-bar-light: linear-gradient(90deg, #3f3f46 0%, #a1a1aa 100%) !important;
  --grad-bar-subtle: linear-gradient(90deg, #52525b 0%, #d4d4d8 100%) !important;

  --shadow-subtle: 0 8px 24px -4px rgba(0, 0, 0, 0.04), 0 2px 6px -1px rgba(0, 0, 0, 0.02) !important;
  --shadow-elevated: 0 16px 36px -6px rgba(0, 0, 0, 0.07), 0 4px 10px -2px rgba(0, 0, 0, 0.03) !important;
}

[data-theme="dark"] {
  --bg-base: #09090b !important;
  --bg-panel: #111114 !important;
  --bg-card: #151518 !important;
  --bg-input: #1a1a20 !important;
  --bg-hover: #222228 !important;
  --border: #27272a !important;
  --border-accent: #3f3f46 !important;
  --border-focus: #f4f4f5 !important;
  --text-primary: #fafafa !important;
  --text-secondary: #a1a1aa !important;
  --text-muted: #71717a !important;

  --grad-hero: linear-gradient(135deg, #000000 0%, #141418 100%) !important;
  --grad-card: linear-gradient(180deg, #18181c 0%, #111114 100%) !important;
  --grad-card-raised: linear-gradient(145deg, #1c1c22 0%, #131317 100%) !important;
  --grad-pearl: linear-gradient(145deg, #18181c 0%, #111114 100%) !important;
  --grad-silver: linear-gradient(135deg, #27272a 0%, #18181b 100%) !important;
  --grad-dark-btn: linear-gradient(135deg, #fafafa 0%, #d4d4d8 100%) !important;
  --grad-bar-dark: linear-gradient(90deg, #fafafa 0%, #a1a1aa 100%) !important;
  --grad-bar-mid: linear-gradient(90deg, #d4d4d8 0%, #71717a 100%) !important;
  --grad-bar-light: linear-gradient(90deg, #a1a1aa 0%, #52525b 100%) !important;
  --grad-bar-subtle: linear-gradient(90deg, #71717a 0%, #3f3f46 100%) !important;

  --shadow-subtle: 0 8px 28px rgba(0, 0, 0, 0.45) !important;
  --shadow-elevated: 0 18px 44px rgba(0, 0, 0, 0.65) !important;
}

/* Base Body y Fondo */
body {
  background: var(--bg-base) !important;
  color: var(--text-primary) !important;
  font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
}

/* ==========================================================================
   TIPOGRAFA FORMAL & CURSIVAS ELEGANTES (CON PROPORCIN CONTROLADA)
   ========================================================================== */

/* Ttulos de pgina y cabeceras principales con estilo editorial */
h1, h2, h3,
.modular-page-title,
.split-panel-title,
.card-section-title,
.patient-name-display,
.report-doc-title,
.inspector-date-title,
.patients-page-title,
.agenda-month-title,
.ecg-main-label {
  font-family: 'Playfair Display', Georgia, 'Times New Roman', serif !important;
  font-style: italic !important;
  font-weight: 600 !important;
  letter-spacing: -0.02em !important;
}

/* Subttulos elegantes en cursiva sutil */
.modular-page-subtitle,
.split-panel-desc,
.patients-page-sub,
.ecg-last-checked,
.report-doc-meta,
.module-eyebrow,
.metric-card-label {
  font-style: italic !important;
  letter-spacing: 0.02em !important;
}

/* Etiquetas destacadas y mtricas auxiliares */
.module-eyebrow,
.picker-label,
.inspector-day-badge,
.spec-label,
.meta-label {
  font-style: italic !important;
  font-size: 11px !important;
  letter-spacing: 0.06em !important;
  color: var(--text-muted) !important;
}

/* ==========================================================================
   SIDEBAR FORMAL B&W CON TOQUES DEGRADADOS
   ========================================================================== */
.sidebar {
  background: var(--bg-panel) !important;
  border-right: 1px solid var(--border) !important;
}

.sidebar-brand-name {
  font-family: 'Playfair Display', Georgia, serif !important;
  font-style: italic !important;
  font-weight: 700 !important;
  letter-spacing: -0.03em !important;
}

.sidebar-nav-section-title {
  font-style: italic !important;
  font-weight: 600 !important;
  font-size: 11px !important;
  letter-spacing: 0.08em !important;
  color: var(--text-muted) !important;
}

.sidebar-nav-btn {
  background: transparent !important;
  color: var(--text-secondary) !important;
  border: 1px solid transparent !important;
  border-radius: 12px !important;
  transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1) !important;
}

.sidebar-nav-btn span {
  font-weight: 500 !important;
}

.sidebar-nav-btn:hover {
  background: var(--bg-hover) !important;
  color: var(--text-primary) !important;
}

/* Botn Activo de la barra lateral: Degradado Obsidiano de Alta Costura */
.sidebar-nav-btn.active {
  background: var(--grad-hero) !important;
  color: #ffffff !important;
  border: 1px solid rgba(255, 255, 255, 0.12) !important;
  box-shadow: 0 8px 22px rgba(0, 0, 0, 0.22) !important;
  transform: translateX(3px) !important;
}

.sidebar-nav-btn.active svg {
  color: #ffffff !important;
  filter: drop-shadow(0 0 6px rgba(255, 255, 255, 0.35)) !important;
}

.sidebar-nav-btn.active span {
  font-style: italic !important;
  font-weight: 600 !important;
}

/* Ajuste oscuro para la barra activa */
[data-theme="dark"] .sidebar-nav-btn.active {
  background: linear-gradient(135deg, #ffffff 0%, #e4e4e7 100%) !important;
  color: #09090b !important;
  border: 1px solid rgba(255, 255, 255, 0.3) !important;
  box-shadow: 0 8px 24px rgba(255, 255, 255, 0.14) !important;
}

[data-theme="dark"] .sidebar-nav-btn.active svg {
  color: #09090b !important;
}

/* ==========================================================================
   TOPBAR EDITORIAL B&W
   ========================================================================== */
.topbar {
  background: var(--bg-panel) !important;
  border-bottom: 1px solid var(--border) !important;
}

.topbar-search-wrap,
.search-box {
  background: var(--bg-input) !important;
  border: 1px solid var(--border) !important;
  border-radius: 999px !important;
}

.topbar-search-input {
  background: transparent !important;
  color: var(--text-primary) !important;
  font-style: italic !important;
}

.topbar-theme-pill {
  background: var(--grad-card-raised) !important;
  border: 1px solid var(--border-accent) !important;
  color: var(--text-primary) !important;
  font-style: italic !important;
  font-weight: 600 !important;
  border-radius: 999px !important;
  box-shadow: var(--shadow-subtle) !important;
}

.topbar-theme-pill:hover {
  background: var(--grad-silver) !important;
}

/* ==========================================================================
   TARJETAS MODULARES CON TOQUES DEGRADADOS (RESUMEN / DASHBOARD)
   ========================================================================== */
.modular-card,
.vital-stat-tile,
.consultation-card,
.metric-card,
.timeline-card,
.reports-kpi-card {
  background: var(--grad-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 20px !important;
  box-shadow: var(--shadow-subtle) !important;
  transition: transform 0.25s ease, box-shadow 0.25s ease, border-color 0.25s ease !important;
}

.modular-card:hover {
  box-shadow: var(--shadow-elevated) !important;
  border-color: var(--border-accent) !important;
}

/* Tarjeta Perfil Paciente */
.patient-hero-card {
  background: var(--grad-card-raised) !important;
}

.patient-name-display {
  font-size: 23px !important;
}

.patient-avatar-large {
  background: var(--grad-hero) !important;
  color: #ffffff !important;
  font-family: 'Playfair Display', Georgia, serif !important;
  font-style: italic !important;
  font-weight: 700 !important;
  border: 2px solid rgba(255, 255, 255, 0.15) !important;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.18) !important;
}

/* Chip de Alergia: Fondo Negro Elegante con tipografa en cursiva */
.patient-allergies-chip-bar .allergy-tag {
  background: #09090b !important;
  color: #ffffff !important;
  border: 1px solid #27272a !important;
  font-style: italic !important;
  font-size: 11.5px !important;
  padding: 5px 12px !important;
  border-radius: 999px !important;
  box-shadow: 0 3px 10px rgba(0,0,0,0.12) !important;
}

[data-theme="dark"] .patient-allergies-chip-bar .allergy-tag {
  background: #27272a !important;
  color: #f4f4f5 !important;
  border: 1px solid #3f3f46 !important;
}

/* Tarjeta ECG y Telemetra: Degradado monocromtico elegante */
.ecg-live-card {
  background: var(--grad-card-raised) !important;
}

.ecg-title-badge .ecg-check-icon {
  background: var(--grad-hero) !important;
  color: #ffffff !important;
  border: 1px solid var(--border-accent) !important;
}

.ecg-bpm-giant .bpm-num {
  font-family: 'Plus Jakarta Sans', sans-serif !important;
  font-style: normal !important;
  font-variant-numeric: tabular-nums !important;
  font-weight: 800 !important;
  color: var(--text-primary) !important;
  letter-spacing: -1px !important;
}

.ecg-bpm-giant .bpm-unit {
  font-family: 'Playfair Display', Georgia, serif !important;
  font-style: italic !important;
  font-weight: 600 !important;
  color: var(--text-muted) !important;
}

/* Barras del Grfico ECG: Degradado plateado / carbn */
.ecg-bar {
  background: linear-gradient(180deg, #18181b 0%, #71717a 100%) !important;
  border-radius: 4px !important;
  opacity: 0.85 !important;
}

[data-theme="dark"] .ecg-bar {
  background: linear-gradient(180deg, #fafafa 0%, #71717a 100%) !important;
}

/* Barras de Progreso (Health Overview, Recovery, Medication, Steps) en Degradados B&W */
.metric-prog-track,
.stat-progress-bar {
  background: var(--bg-input) !important;
  border: 1px solid var(--border) !important;
  border-radius: 999px !important;
}

.metric-prog-fill.fill-blue,
.stat-progress-bar > div:nth-child(1) {
  background: var(--grad-bar-dark) !important;
}

.metric-prog-fill.fill-amber,
.stat-progress-bar > div:nth-child(2) {
  background: var(--grad-bar-mid) !important;
}

.metric-prog-fill.fill-green,
.stat-progress-bar > div:nth-child(3) {
  background: var(--grad-bar-light) !important;
}

.metric-prog-fill.fill-purple {
  background: var(--grad-bar-subtle) !important;
}

/* Tarjeta de Reporte Mdico */
.medical-report-card {
  background: var(--grad-card-raised) !important;
}

.btn-report-view {
  background: var(--grad-silver) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border-accent) !important;
  font-style: italic !important;
  font-weight: 600 !important;
  border-radius: 999px !important;
}

.btn-report-view:hover {
  background: var(--bg-hover) !important;
}

.btn-report-download {
  background: var(--grad-hero) !important;
  color: #ffffff !important;
  border: 1px solid rgba(255, 255, 255, 0.1) !important;
  font-style: italic !important;
  font-weight: 600 !important;
  border-radius: 999px !important;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.2) !important;
}

.btn-report-download:hover {
  opacity: 0.92 !important;
  transform: translateY(-1px) !important;
}

/* Pastillas de Eventos Cronolgicos (Timeline) */
.timeline-event-pill {
  background: var(--grad-card) !important;
  border: 1px solid var(--border) !important;
  box-shadow: var(--shadow-subtle) !important;
}

.timeline-event-pill strong {
  font-style: italic !important;
  font-family: 'Playfair Display', Georgia, serif !important;
}

.timeline-event-pill span {
  font-style: italic !important;
}

/* ==========================================================================
   NUEVA CONSULTA - WORKSTATION EDITORIAL B&W
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
  box-shadow: var(--shadow-subtle) !important;
}

/* Selector de mtodo de captura: Audio, Texto, Transcripcin */
.capture-mode-btn,
.mode-switch-btn,
.tab-pill {
  background: var(--bg-input) !important;
  color: var(--text-secondary) !important;
  border: 1px solid var(--border) !important;
  border-radius: 999px !important;
  font-weight: 500 !important;
  transition: all 0.2s ease !important;
}

.capture-mode-btn.active,
.mode-switch-btn.active,
.tab-pill.active {
  background: var(--grad-hero) !important;
  color: #ffffff !important;
  border-color: #000000 !important;
  font-style: italic !important;
  font-weight: 600 !important;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.18) !important;
}

[data-theme="dark"] .capture-mode-btn.active,
[data-theme="dark"] .mode-switch-btn.active,
[data-theme="dark"] .tab-pill.active {
  background: linear-gradient(135deg, #ffffff 0%, #e4e4e7 100%) !important;
  color: #09090b !important;
}

/* Plantillas Rpidas con Cursiva */
.quick-template-chip,
.template-pill-btn {
  background: var(--grad-card) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border-accent) !important;
  font-style: italic !important;
  border-radius: 999px !important;
}

.quick-template-chip:hover,
.template-pill-btn:hover {
  background: var(--grad-hero) !important;
  color: #ffffff !important;
  border-color: #09090b !important;
}

/* Botones de Accin Clnica Principales */
.btn-primary-action,
.btn-save-note,
.btn-dark-pill,
.btn-register-patient-modern {
  background: var(--grad-hero) !important;
  color: #ffffff !important;
  border: 1px solid rgba(255, 255, 255, 0.12) !important;
  border-radius: 999px !important;
  font-style: italic !important;
  font-weight: 600 !important;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2) !important;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
}

.btn-primary-action:hover,
.btn-save-note:hover,
.btn-dark-pill:hover,
.btn-register-patient-modern:hover {
  opacity: 0.94 !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.28) !important;
}

/* ==========================================================================
   DR. OSO FLOTANTE & CHAT MODULAR EN BLANCO Y NEGRO EDITORIAL
   ========================================================================== */

/* Botn Flotante FAB con Ncar Perlado y Borde Metlico */
.pulso-fab-btn {
  background: radial-gradient(circle at 50% 50%, #ffffff 0%, #f4f4f6 68%, #e4e4e7 100%) !important;
  border: 2px solid #27272a !important;
  box-shadow: 0 14px 32px rgba(0, 0, 0, 0.22), 0 0 0 1px rgba(255, 255, 255, 0.6) !important;
}

[data-theme="dark"] .pulso-fab-btn {
  background: radial-gradient(circle at 50% 50%, #27272a 0%, #18181b 70%, #09090b 100%) !important;
  border: 2px solid #71717a !important;
  box-shadow: 0 14px 36px rgba(0, 0, 0, 0.75) !important;
}

/* Panel de Chat de Dr. Oso: B&W Formal */
.pulso-chat-panel {
  background: var(--bg-panel) !important;
  border: 1.5px solid var(--border-focus) !important;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.32) !important;
  border-radius: 22px !important;
}

.pulso-chat-header {
  background: var(--grad-hero) !important;
  border-bottom: 1.5px solid #27272a !important;
  color: #ffffff !important;
}

.pulso-chat-title {
  font-family: 'Playfair Display', Georgia, serif !important;
  font-style: italic !important;
  font-weight: 600 !important;
  font-size: 15px !important;
  letter-spacing: -0.01em !important;
}

.pulso-conn-dot {
  background: #22c55e !important;
}

/* Burbujas de Chat: Blanco y Negro Refinado */
.pulso-msg-user .pulso-msg-bubble {
  background: var(--grad-hero) !important;
  color: #ffffff !important;
  border-radius: 16px 16px 2px 16px !important;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
}

.pulso-msg-assistant .pulso-msg-bubble {
  background: var(--grad-card) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border) !important;
  border-radius: 16px 16px 16px 2px !important;
  box-shadow: var(--shadow-subtle) !important;
}

.pulso-chat-footer {
  background: var(--bg-panel) !important;
  border-top: 1px solid var(--border) !important;
}

.pulso-chat-input {
  background: var(--bg-input) !important;
  color: var(--text-primary) !important;
  border: 1px solid var(--border) !important;
  border-radius: 12px !important;
}

.pulso-send-btn {
  background: var(--grad-hero) !important;
  color: #ffffff !important;
  border-radius: 12px !important;
  box-shadow: 0 4px 12px rgba(0,0,0,0.2) !important;
}

/* ==========================================================================
   CONCISIN & DETALLES DE LUJO EDITORIAL
   ========================================================================== */

/* Citas y Calendario */
.cal-legend-bar {
  background: var(--grad-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 14px !important;
}

.cal-legend-summary {
  font-style: italic !important;
}

/* Tabla de Pacientes */
.patient-table th {
  font-style: italic !important;
  letter-spacing: 0.04em !important;
}

.patient-table td strong {
  font-family: 'Playfair Display', Georgia, serif !important;
  font-style: italic !important;
}
"""

def update_css(base_dir):
    p = os.path.join(base_dir, "frontend", "style.css")
    if not os.path.exists(p):
        return
    with open(p, "r", encoding="utf-8") as f:
        content = f.read()

    marker = "/* ==========================================================================\n   FORMAL ELEGANT BLACK & WHITE EDITORIAL CLINICAL THEME"
    if marker in content:
        idx = content.find(marker)
        content = content[:idx] + BW_THEME_CSS.strip() + "\n"
    else:
        content = content + "\n\n" + BW_THEME_CSS.strip() + "\n"

    with open(p, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Applied B&W Editorial Theme to {p}")

def update_html(base_dir):
    p = os.path.join(base_dir, "frontend", "index.html")
    if not os.path.exists(p):
        return
    with open(p, "r", encoding="utf-8") as f:
        html = f.read()

    # Add Playfair Display font link if not present
    if "family=Playfair+Display" not in html:
        old_font_link = '<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans'
        new_font_link = '<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,500;0,600;0,700;1,400;1,500;1,600;1,700&family=Plus+Jakarta+Sans'
        if old_font_link in html:
            html = html.replace(old_font_link, new_font_link)
            with open(p, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"Added Playfair Display font link to {p}")
        else:
            print(f"Font link pattern not matched in {p}")
    else:
        print(f"Playfair Display font already present in {p}")

for root in ROOTS:
    update_css(root)
    update_html(root)

print("Editorial B&W Theme fully applied.")
