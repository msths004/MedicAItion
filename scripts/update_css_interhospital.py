"""
update_css_interhospital.py — Inyección de estilos CSS para Red Hospitalaria Federada
"""

import os

CSS_PATH = os.path.abspath("frontend/style.css")
LINUX_CSS = os.path.abspath("Linux_Ver/frontend/style.css")

CSS_STYLES = """
/* =========================================================================
   RED HOSPITALARIA & INTERCONSULTA FEDERADA (NOM-024 / HL7 FHIR R4)
   ========================================================================= */

/* Topbar Hospital Network Pill */
.hospital-network-pill {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(2, 132, 199, 0.08);
  border: 1px solid rgba(2, 132, 199, 0.22);
  padding: 5px 12px;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
}
.hospital-network-pill:hover {
  background: rgba(2, 132, 199, 0.14);
  border-color: #0284c7;
  transform: translateY(-1px);
}
.hosp-net-icon {
  font-size: 14px;
}
.hosp-net-info {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
}
.hosp-net-title {
  font-size: 11px;
  font-weight: 700;
  color: #0369a1;
}
.hosp-net-sub {
  font-size: 10px;
  color: #64748b;
  font-weight: 500;
}
.hosp-net-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 0 2px rgba(16, 185, 129, 0.25);
  animation: pulse-green 2s infinite;
}

@keyframes pulse-green {
  0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
  70% { transform: scale(1); box-shadow: 0 0 0 6px rgba(16, 185, 129, 0); }
  100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}

/* Container */
.red-hospital-container {
  padding: 24px 32px;
  max-width: 1400px;
  margin: 0 auto;
}

/* Header */
.red-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}
.red-title-tag {
  display: flex;
  gap: 8px;
  margin-bottom: 6px;
}
.red-tag-badge {
  background: #e0f2fe;
  color: #0369a1;
  font-size: 10.5px;
  font-weight: 800;
  padding: 3px 8px;
  border-radius: 6px;
  letter-spacing: 0.4px;
}
.red-tag-badge-accent {
  background: #ecfdf5;
  color: #047857;
  font-size: 10.5px;
  font-weight: 800;
  padding: 3px 8px;
  border-radius: 6px;
}
.red-header h1 {
  font-size: 24px;
  font-weight: 800;
  color: #0f172a;
  margin: 0 0 6px 0;
  letter-spacing: -0.3px;
}
.red-header p {
  margin: 0;
  font-size: 13.5px;
  color: #64748b;
  max-width: 820px;
  line-height: 1.5;
}
.red-header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
}

/* Bento KPI Grid */
.red-kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}
.red-kpi-card {
  padding: 18px 20px;
  border-radius: 14px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px rgba(0,0,0,0.02);
}
.red-kpi-card .bento-label {
  font-size: 11px;
  font-weight: 800;
  color: #64748b;
  letter-spacing: 0.5px;
  margin-bottom: 6px;
}
.red-kpi-card .bento-value {
  font-size: 26px;
  font-weight: 900;
  color: #0f172a;
  line-height: 1.1;
  margin-bottom: 4px;
}
.red-kpi-card .bento-value.text-accent { color: #0284c7; }
.red-kpi-card .bento-value.text-success { color: #059669; }
.red-kpi-card .bento-value.text-amber { color: #d97706; }
.red-kpi-card .bento-desc {
  font-size: 11.5px;
  color: #94a3b8;
}

/* Red Search Card */
.red-search-card {
  background: #ffffff;
  border-radius: 16px;
  padding: 24px;
  border: 1px solid #e2e8f0;
  margin-bottom: 24px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.03);
}
.access-mode-toggle {
  display: flex;
  background: #f1f5f9;
  padding: 4px;
  border-radius: 12px;
  gap: 4px;
}
.mode-toggle-btn {
  border: none;
  background: transparent;
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 12.5px;
  font-weight: 700;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s ease;
}
.mode-toggle-btn.active {
  background: #ffffff;
  color: #0284c7;
  box-shadow: 0 2px 4px rgba(0,0,0,0.06);
}
.mode-toggle-btn#btn-mode-urgencias.active {
  color: #dc2626;
}

.red-search-controls {
  margin-top: 18px;
}
.red-search-input-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #f8fafc;
  border: 1.5px solid #cbd5e1;
  padding: 6px 8px 6px 16px;
  border-radius: 12px;
  transition: all 0.2s;
}
.red-search-input-wrap:focus-within {
  border-color: #0284c7;
  background: #ffffff;
  box-shadow: 0 0 0 3px rgba(2, 132, 199, 0.12);
}
.red-search-input-wrap input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 14px;
  color: #0f172a;
  outline: none;
}
.red-quick-pills {
  display: flex;
  gap: 8px;
  align-items: center;
  flex-wrap: wrap;
  margin-top: 10px;
}
.quick-curp-pill {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 11.5px;
  color: #475569;
  cursor: pointer;
  transition: all 0.15s;
}
.quick-curp-pill:hover {
  background: #e0f2fe;
  color: #0284c7;
  border-color: #7dd3fc;
}

/* Safe Harbor Banner */
.safe-harbor-info-banner {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 12px 16px;
  border-radius: 12px;
  margin-top: 14px;
  font-size: 12px;
  line-height: 1.45;
}
.safe-harbor-info-banner.mode-urgencias {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
}
.safe-harbor-info-banner.mode-interconsulta {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #166534;
}
.safe-harbor-info-banner .sh-icon {
  font-size: 20px;
  line-height: 1;
}
.safe-harbor-info-banner .sh-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

/* Network Patient Result Card */
.network-patient-card {
  background: #ffffff;
  border: 1.5px solid #0284c7;
  border-radius: 16px;
  padding: 22px;
  box-shadow: 0 8px 24px rgba(2, 132, 199, 0.08);
  animation: fadeIn 0.3s ease;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}
.net-pat-header {
  display: flex;
  align-items: center;
  gap: 16px;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.net-pat-avatar {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  background: linear-gradient(135deg, #0284c7, #0369a1);
  color: #ffffff;
  font-size: 20px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
}
.net-pat-main-info {
  flex: 1;
}
.net-pat-name-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.net-pat-name-row h3 {
  font-size: 19px;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
}
.blood-group-badge {
  background: #fee2e2;
  color: #b91c1c;
  font-size: 12px;
  font-weight: 800;
  padding: 3px 8px;
  border-radius: 6px;
}
.privacy-seal-badge {
  background: #e0f2fe;
  color: #0369a1;
  font-size: 11px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 6px;
}
.net-pat-curp-row {
  font-size: 12.5px;
  color: #64748b;
  margin-top: 4px;
}
.net-pat-actions {
  display: flex;
  gap: 8px;
}

/* Grid of Clinical Safeguards */
.net-pat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}
.net-info-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 14px;
}
.net-info-box.alert-box {
  background: #fff5f5;
  border-color: #fecaca;
}
.nib-label {
  font-size: 10.5px;
  font-weight: 800;
  color: #64748b;
  letter-spacing: 0.5px;
  margin-bottom: 8px;
}
.net-info-box.alert-box .nib-label {
  color: #b91c1c;
}
.nib-content {
  font-size: 13px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.allergy-tag-urgent {
  background: #fee2e2;
  color: #991b1b;
  font-size: 12px;
  font-weight: 800;
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid #f87171;
}
.med-tag-active {
  background: #e0f2fe;
  color: #0369a1;
  font-size: 12px;
  font-weight: 700;
  padding: 4px 8px;
  border-radius: 6px;
}
.dx-tag-key {
  background: #f1f5f9;
  color: #334155;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 8px;
  border-radius: 6px;
}

/* Connected Hospitals Section */
.net-connected-hospitals-section {
  background: #f8fafc;
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 14px;
}
.nch-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  margin-bottom: 10px;
}
.nch-list {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.hosp-record-pill {
  display: flex;
  align-items: center;
  gap: 10px;
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 8px 12px;
  flex: 1;
  min-width: 240px;
}
.hr-icon {
  font-size: 18px;
}
.hr-content {
  display: flex;
  flex-direction: column;
  flex: 1;
}
.hr-content strong {
  font-size: 12.5px;
  color: #0f172a;
}
.hr-sub {
  font-size: 11px;
  color: #64748b;
}
.hr-badge-clues {
  background: #f1f5f9;
  color: #475569;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: monospace;
}

/* Privacy Guarantee Bar */
.net-privacy-guarantee-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11.5px;
  color: #475569;
  border-top: 1px solid #e2e8f0;
  padding-top: 12px;
  flex-wrap: wrap;
  gap: 8px;
}
.hmac-tag {
  font-family: monospace;
  font-size: 10.5px;
  background: #f1f5f9;
  padding: 3px 6px;
  border-radius: 4px;
  color: #0369a1;
}

/* Two-Column Grid */
.red-two-col {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 20px;
  margin-top: 20px;
}
@media (max-width: 1024px) {
  .red-two-col {
    grid-template-columns: 1fr;
  }
}

/* Tables */
.referrals-table-wrap {
  overflow-x: auto;
}
.red-data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  text-align: left;
}
.red-data-table th {
  background: #f8fafc;
  padding: 10px 12px;
  font-size: 11px;
  font-weight: 800;
  color: #64748b;
  border-bottom: 1.5px solid #e2e8f0;
  letter-spacing: 0.4px;
}
.red-data-table td {
  padding: 12px;
  border-bottom: 1px solid #f1f5f9;
  color: #1e293b;
  vertical-align: middle;
}
.red-data-table tr:hover {
  background: #f8fafc;
}

/* Status & Priority Badges */
.ref-prio-badge {
  display: inline-block;
  font-size: 11px;
  font-weight: 800;
  padding: 3px 8px;
  border-radius: 6px;
}
.ref-prio-badge.prio-urgent { background: #fee2e2; color: #dc2626; }
.ref-prio-badge.prio-high { background: #fef3c7; color: #d97706; }
.ref-prio-badge.prio-normal { background: #f1f5f9; color: #475569; }

.ref-state-badge {
  display: inline-block;
  font-size: 11.5px;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 6px;
}
.ref-state-badge.state-transit { background: #fef3c7; color: #b45309; }
.ref-state-badge.state-accepted { background: #e0f2fe; color: #0284c7; }
.ref-state-badge.state-completed { background: #dcfce7; color: #15803d; }
.ref-state-badge.state-pending { background: #f1f5f9; color: #64748b; }

.ref-action-select {
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid #cbd5e1;
  font-size: 11.5px;
  background: #ffffff;
  color: #334155;
  cursor: pointer;
}

/* Hospital Node Cards */
.hospital-nodes-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.hosp-node-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px 14px;
  transition: all 0.2s;
}
.hosp-node-card.is-local-base {
  background: #f0fdf4;
  border-color: #86efac;
}
.hosp-node-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.hosp-node-title-box {
  display: flex;
  align-items: center;
  gap: 10px;
}
.hosp-node-emoji {
  font-size: 18px;
}
.hosp-node-name {
  font-size: 13px;
  font-weight: 800;
  color: #0f172a;
}
.hosp-node-clues {
  font-size: 11px;
  color: #64748b;
}
.hosp-status-pill {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 10px;
}
.hosp-status-pill.is-online {
  background: #e0f2fe;
  color: #0369a1;
}
.hosp-status-pill.is-local {
  background: #dcfce7;
  color: #15803d;
}
.hosp-node-meta {
  display: flex;
  gap: 8px;
  margin-top: 6px;
}
.meta-tag {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10.5px;
  color: #64748b;
  font-weight: 600;
}

.audit-badge-hmac {
  background: #ecfdf5;
  color: #047857;
  font-size: 11px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 4px;
  border: 1px solid #a7f3d0;
}
"""

with open(CSS_PATH, "r", encoding="utf-8") as f:
    css = f.read()

if "RED HOSPITALARIA & INTERCONSULTA FEDERADA" not in css:
    css += "\n" + CSS_STYLES
    with open(CSS_PATH, "w", encoding="utf-8") as f:
        f.write(css)
    print("Estilos inyectados en frontend/style.css.")
else:
    print("Estilos ya presentes en frontend/style.css.")

if os.path.exists(LINUX_CSS):
    with open(LINUX_CSS, "r", encoding="utf-8") as f:
        lcss = f.read()
    if "RED HOSPITALARIA & INTERCONSULTA FEDERADA" not in lcss:
        lcss += "\n" + CSS_STYLES
        with open(LINUX_CSS, "w", encoding="utf-8") as f:
            f.write(lcss)
        print("Sincronizado a Linux_Ver/frontend/style.css.")
