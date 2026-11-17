# -*- coding: utf-8 -*-
import os

BASE_DIR = r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion"
STYLE_PATH = os.path.join(BASE_DIR, "frontend", "style.css")
LINUX_STYLE_PATH = os.path.join(BASE_DIR, "Linux_Ver", "frontend", "style.css")

with open(STYLE_PATH, "r", encoding="utf-8") as f:
    css = f.read()

modular_css = """
/* ==========================================================================
   MODULAR PATIENT PROFILE & CLINICAL DASHBOARD (1:1 FIDELITY RECREATION)
   Inspirado en media_1794700216734_e9ed90ad.jpg y frame_50.jpg
   ========================================================================== */

.modular-dashboard-wrapper {
  max-width: 1560px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 22px;
  padding: 10px 16px 36px 16px;
  animation: fadeInView 0.35s ease-out;
}

/* TOPBAR ACTIONS STRIP */
.modular-topbar-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
  padding-bottom: 6px;
}

.modular-page-title {
  font-size: 24px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.5px;
  margin: 0 0 3px 0;
}

.modular-page-subtitle {
  font-size: 13px;
  color: var(--text-muted);
  font-weight: 600;
}

.modular-topbar-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.modular-patient-picker {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--bg-card);
  border: 1.5px solid var(--border);
  padding: 5px 12px;
  border-radius: 999px;
}

.picker-label {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.6px;
  color: var(--text-muted);
}

.modular-select-pill {
  border: none;
  background: transparent;
  color: var(--text-primary);
  font-size: 12.5px;
  font-weight: 700;
  outline: none;
  cursor: pointer;
}

.btn-modular-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  border-radius: 999px;
  background: var(--blue-accent);
  color: #ffffff;
  border: none;
  font-size: 13.5px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 4px 14px rgba(2, 132, 199, 0.28);
}

.btn-modular-primary:hover {
  background: #0369a1;
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(2, 132, 199, 0.38);
}

/* MODULAR CARD BASE */
.modular-card {
  background: var(--bg-panel);
  border: 1.5px solid var(--border);
  border-radius: 26px;
  padding: 24px;
  box-shadow: var(--shadow-panel);
  transition: border-color 0.25s ease, box-shadow 0.25s ease;
  min-width: 0;
}

.modular-card:hover {
  border-color: var(--border-accent);
}

.module-eyebrow {
  font-size: 11px;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.8px;
  color: var(--blue-accent);
}

.patient-card-options-btn,
.ecg-header-options,
.kpi-dots,
.header-dots {
  color: var(--text-muted);
  font-size: 16px;
  font-weight: 900;
  cursor: pointer;
  letter-spacing: 2px;
}

/* ROW 1: HERO (PATIENT CARD + LIVE ECG) */
.modular-grid-row.row-hero {
  display: grid;
  grid-template-columns: 1.15fr 1fr;
  gap: 22px;
}

@media (max-width: 1100px) {
  .modular-grid-row.row-hero {
    grid-template-columns: 1fr;
  }
}

.patient-hero-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.patient-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.patient-hero-body {
  display: flex;
  align-items: center;
  gap: 24px;
}

@media (max-width: 640px) {
  .patient-hero-body {
    flex-direction: column;
    align-items: flex-start;
  }
}

.patient-photo-container {
  position: relative;
  flex-shrink: 0;
}

.patient-avatar-large {
  width: 84px;
  height: 84px;
  border-radius: 24px;
  background: linear-gradient(135deg, #0284c7 0%, #0f766e 100%);
  color: #ffffff;
  font-size: 28px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 10px 24px rgba(2, 132, 199, 0.28);
}

.patient-status-indicator-dot {
  position: absolute;
  bottom: 0px;
  right: 0px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 3px solid var(--bg-panel);
}

.patient-status-indicator-dot.online {
  background: #10b981;
}

.patient-hero-details {
  flex: 1;
  min-width: 0;
}

.patient-name-display {
  font-size: 20px;
  font-weight: 800;
  color: var(--text-primary);
  margin: 0 0 10px 0;
  letter-spacing: -0.4px;
}

.patient-specs-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px 14px;
  margin-bottom: 12px;
}

@media (max-width: 760px) {
  .patient-specs-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

.spec-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.spec-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
}

.spec-val {
  font-size: 13px;
  font-weight: 700;
  color: var(--text-primary);
}

.spec-val.blood-highlight {
  color: #ef4444;
  font-weight: 800;
}

.patient-allergies-chip-bar {
  margin-top: 4px;
}

.allergy-tag {
  display: inline-block;
  font-size: 11.5px;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 8px;
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border: 1px solid rgba(239, 68, 68, 0.25);
}

[data-theme="light"] .allergy-tag {
  background: #fef2f2;
  color: #991b1b;
  border-color: #fca5a5;
}

/* ECG CARD */
.ecg-live-card {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.ecg-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.ecg-title-badge {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ecg-check-icon {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: rgba(16, 185, 129, 0.15);
  color: #10b981;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 900;
  border: 1.5px solid rgba(16, 185, 129, 0.35);
}

.ecg-main-label {
  font-size: 13px;
  font-weight: 800;
  color: var(--text-primary);
}

.ecg-last-checked {
  font-size: 11px;
  color: var(--text-muted);
  font-weight: 600;
}

.ecg-telemetry-meta-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 10px 18px;
}

.ecg-meta-col {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.meta-label {
  font-size: 10.5px;
  font-weight: 600;
  color: var(--text-muted);
}

.meta-val {
  font-size: 12.5px;
  font-weight: 700;
  color: var(--text-primary);
}

.meta-val.status-normal {
  color: #10b981;
}

.ecg-bpm-giant {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.bpm-num {
  font-size: 34px;
  font-weight: 800;
  color: var(--text-primary);
  font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
}

.bpm-unit {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-muted);
}

/* ECG BARS + SVG WAVE OVERLAY */
.ecg-digital-graph-wrap {
  position: relative;
  height: 72px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 10px 14px;
  overflow: hidden;
  display: flex;
  align-items: flex-end;
}

.ecg-bars-equalizer {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  width: 100%;
  height: 100%;
  gap: 4px;
}

.ecg-bars-equalizer span {
  flex: 1;
  background: rgba(2, 132, 199, 0.22);
  border-radius: 3px;
  transition: height 0.3s ease;
}

[data-theme="dark"] .ecg-bars-equalizer span {
  background: rgba(56, 189, 248, 0.25);
}

.ecg-line-overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

/* ROW 2: 4 METRICS CARDS (HORIZONTAL) */
.modular-metrics-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 18px;
}

@media (max-width: 960px) {
  .modular-metrics-row {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 520px) {
  .modular-metrics-row {
    grid-template-columns: 1fr;
  }
}

.kpi-metric-card {
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.kpi-metric-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.kpi-metric-name {
  font-size: 12px;
  font-weight: 700;
  color: var(--text-muted);
}

.kpi-metric-val-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-top: 2px;
}

.kpi-metric-number {
  font-size: 26px;
  font-weight: 800;
  color: var(--text-primary);
  font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
}

.kpi-metric-total {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
}

.kpi-delta-pill {
  font-size: 11px;
  font-weight: 800;
  padding: 2px 7px;
  border-radius: 999px;
}

.delta-up {
  background: rgba(16, 185, 129, 0.12);
  color: #10b981;
}

.delta-down {
  background: rgba(239, 68, 68, 0.12);
  color: #ef4444;
}

.kpi-progress-track {
  width: 100%;
  height: 8px;
  background: var(--bg-card);
  border-radius: 999px;
  overflow: hidden;
  margin-top: 4px;
  border: 1px solid var(--border);
}

.kpi-progress-bar {
  height: 100%;
  border-radius: 999px;
  transition: width 0.6s ease;
}

.bar-blue { background: linear-gradient(90deg, #0284c7, #38bdf8); }
.bar-amber { background: linear-gradient(90deg, #f59e0b, #fbbf24); }
.bar-lime { background: linear-gradient(90deg, #10b981, #34d399); }
.bar-purple { background: linear-gradient(90deg, #8b5cf6, #c084fc); }

.kpi-sub-text {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-muted);
}

/* ROW 3: TIMELINE TRACKING + MEDICAL REPORT */
.modular-grid-row.row-bottom {
  display: grid;
  grid-template-columns: 1.35fr 1fr;
  gap: 22px;
}

@media (max-width: 1100px) {
  .modular-grid-row.row-bottom {
    grid-template-columns: 1fr;
  }
}

.card-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.card-section-title {
  margin: 0 0 2px 0;
  font-size: 15.5px;
  font-weight: 800;
  color: var(--text-primary);
  letter-spacing: -0.3px;
}

.card-section-sub {
  font-size: 11.5px;
  color: var(--text-muted);
  font-weight: 600;
}

/* TIMELINE CONTAINER & SLOTS */
.timeline-visual-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.timeline-hours-axis {
  display: flex;
  justify-content: space-between;
  padding: 0 4px;
}

.hour-mark {
  font-size: 10.5px;
  font-weight: 700;
  color: var(--text-muted);
}

.timeline-slots-grid {
  position: relative;
  height: 140px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 18px;
  overflow: hidden;
}

.timeline-guide-line {
  position: absolute;
  top: 0;
  bottom: 0;
  border-left: 1.5px dashed var(--border);
}

.timeline-event-pill {
  position: absolute;
  height: 48px;
  border-radius: 14px;
  padding: 6px 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.05);
  transition: transform 0.2s ease;
  cursor: pointer;
}

.timeline-event-pill:hover {
  transform: translateY(-2px);
}

.event-cyan {
  background: rgba(2, 132, 199, 0.12);
  border: 1.5px solid rgba(2, 132, 199, 0.3);
}

[data-theme="light"] .event-cyan {
  background: #f0f9ff;
  border-color: #bae6fd;
}

.event-green {
  background: rgba(16, 185, 129, 0.12);
  border: 1.5px solid rgba(16, 185, 129, 0.3);
}

[data-theme="light"] .event-green {
  background: #ecfdf5;
  border-color: #a7f3d0;
}

.event-amber {
  background: rgba(245, 158, 11, 0.12);
  border: 1.5px solid rgba(245, 158, 11, 0.3);
}

[data-theme="light"] .event-amber {
  background: #fffbeb;
  border-color: #fde68a;
}

.event-icon-circle {
  font-size: 16px;
  flex-shrink: 0;
}

.event-pill-content {
  display: flex;
  flex-direction: column;
  min-width: 0;
  flex: 1;
}

.event-pill-content strong {
  font-size: 11.5px;
  font-weight: 800;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.event-pill-content span {
  font-size: 10px;
  color: var(--text-secondary);
  font-weight: 600;
}

.event-status-check {
  font-size: 11px;
  font-weight: 900;
  color: #10b981;
}

.event-status-check.pulse-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f59e0b;
  box-shadow: 0 0 8px #f59e0b;
}

/* MEDICAL REPORT CARD */
.medical-report-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.report-card-center-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 12px 10px;
}

.report-illustration-badge {
  width: 68px;
  height: 68px;
  border-radius: 20px;
  background: rgba(2, 132, 199, 0.1);
  border: 1.5px solid rgba(2, 132, 199, 0.22);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}

.report-doc-title {
  margin: 0 0 4px 0;
  font-size: 14.5px;
  font-weight: 800;
  color: var(--text-primary);
}

.report-doc-meta {
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.report-doc-diagnosis {
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-secondary);
  line-height: 1.4;
  margin: 0;
}

.report-card-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-top: 16px;
}

.btn-report-view {
  height: 44px;
  border-radius: 14px;
  border: 1.5px solid var(--border);
  background: var(--bg-card);
  color: var(--text-primary);
  font-size: 12.5px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.2s ease;
}

.btn-report-view:hover {
  background: var(--bg-hover);
  border-color: var(--border-accent);
}

.btn-report-download {
  height: 44px;
  border-radius: 14px;
  border: none;
  background: var(--blue-accent);
  color: #ffffff;
  font-size: 12.5px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: all 0.2s ease;
  box-shadow: 0 4px 14px rgba(2, 132, 199, 0.25);
}

.btn-report-download:hover {
  background: #0369a1;
  transform: translateY(-1px);
}

/* ==========================================================================
   NUEVA CONSULTA WORKSTATION — SPACING & BREATHING ROOM CALIBRATION
   ========================================================================== */
#consulta-layout {
  display: grid !important;
  grid-template-columns: 310px minmax(0, 1fr) 340px !important;
  gap: 22px !important;
  max-width: 1720px !important;
  width: 100% !important;
  margin: 0 auto !important;
  padding: 10px 16px !important;
  box-sizing: border-box !important;
}

@media (max-width: 1380px) {
  #consulta-layout {
    grid-template-columns: 1fr 340px !important;
  }
  #panel-patient-vitals {
    grid-column: 1 / -1 !important;
  }
}

@media (max-width: 900px) {
  #consulta-layout {
    grid-template-columns: 1fr !important;
  }
}
"""

if "MODULAR PATIENT PROFILE & CLINICAL DASHBOARD" not in css:
    with open(STYLE_PATH, "a", encoding="utf-8") as f:
        f.write("\n" + modular_css)
    with open(LINUX_STYLE_PATH, "a", encoding="utf-8") as f:
        f.write("\n" + modular_css)
    print("Appended modular CSS to style.css and Linux_Ver.")
else:
    # Update existing block
    idx_block = css.find("/* ==========================================================================\n   MODULAR PATIENT PROFILE")
    if idx_block != -1:
        css = css[:idx_block] + modular_css
    else:
        css += "\n" + modular_css
    with open(STYLE_PATH, "w", encoding="utf-8") as f:
        f.write(css)
    with open(LINUX_STYLE_PATH, "w", encoding="utf-8") as f:
        f.write(css)
    print("Updated modular CSS block.")

print("CSS updated successfully.")
