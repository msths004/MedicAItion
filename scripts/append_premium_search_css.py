# -*- coding: utf-8 -*-
import os

ROOTS = [
    r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion",
    r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion\Linux_Ver"
]

PREMIUM_SEARCH_CSS = """
/* ==========================================================================
   PREMIUM SEARCH & COMMAND PALETTE (OMNI-SEARCH SPOTLIGHT) - BLANCO Y CELESTE
   ========================================================================== */

/* Modal Backdrop */
.omni-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 99999;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 80px;
  background: rgba(15, 23, 42, 0.45);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  animation: omniFadeIn 0.2s ease-out;
}

@keyframes omniFadeIn {
  from { opacity: 0; transform: scale(0.98); }
  to { opacity: 1; transform: scale(1); }
}

.omni-backdrop {
  position: absolute;
  inset: 0;
}

.omni-dialog {
  position: relative;
  z-index: 10;
  width: 90%;
  max-width: 760px;
  max-height: 82vh;
  display: flex;
  flex-direction: column;
  background: #ffffff;
  border: 1.5px solid #cde0f1;
  border-radius: 22px;
  box-shadow: 0 24px 70px -12px rgba(37, 137, 255, 0.28), 0 8px 24px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

[data-theme="dark"] .omni-dialog {
  background: #111c38;
  border-color: #25467e;
  box-shadow: 0 24px 70px -12px rgba(0, 0, 0, 0.7);
}

/* Header & Input */
.omni-header {
  padding: 18px 22px 14px 22px;
  border-bottom: 1px solid #e2eaf2;
  background: #ffffff;
}

[data-theme="dark"] .omni-header {
  background: #111c38;
  border-color: #1f325e;
}

.omni-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  background: #f4f7fb;
  border: 1.5px solid #cde0f1;
  border-radius: 999px;
  padding: 10px 18px;
  transition: all 0.2s ease;
}

[data-theme="dark"] .omni-input-wrapper {
  background: #152244;
  border-color: #25467e;
}

.omni-input-wrapper:focus-within {
  border-color: #2589ff;
  background: #ffffff;
  box-shadow: 0 0 0 4px rgba(37, 137, 255, 0.15);
}

[data-theme="dark"] .omni-input-wrapper:focus-within {
  background: #1a2a52;
  border-color: #38bdf8;
  box-shadow: 0 0 0 4px rgba(56, 189, 248, 0.18);
}

.omni-search-icon {
  color: #2589ff;
  flex-shrink: 0;
}

.omni-search-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 15.5px;
  font-family: inherit;
  font-weight: 500;
  color: #1e293b;
  outline: none;
}

[data-theme="dark"] .omni-search-input {
  color: #f8fafc;
}

.omni-search-input::placeholder {
  color: #94a3b8;
  font-style: italic;
  font-weight: 400;
}

.omni-clear-btn {
  background: #e2eaf2;
  border: none;
  border-radius: 50%;
  width: 22px;
  height: 22px;
  font-size: 11px;
  color: #64748b;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.15s ease;
}

.omni-clear-btn:hover {
  background: #cbd5e1;
  color: #0f172a;
}

.omni-kbd-badge kbd {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 6px;
  padding: 2px 7px;
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  font-family: monospace;
}

[data-theme="dark"] .omni-kbd-badge kbd {
  background: #1f325e;
  border-color: #2e4a87;
  color: #cbd5e1;
}

/* Category Filter Chips */
.omni-filters-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  overflow-x: auto;
  padding-bottom: 2px;
}

.omni-filter-chip {
  background: #f4f7fb;
  border: 1px solid #e2eaf2;
  color: #475569;
  border-radius: 999px;
  padding: 5px 13px;
  font-size: 12.5px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

[data-theme="dark"] .omni-filter-chip {
  background: #152244;
  border-color: #1f325e;
  color: #94a3b8;
}

.omni-filter-chip:hover {
  background: #eaf3fe;
  color: #2589ff;
  border-color: #c8e1fd;
}

.omni-filter-chip.active {
  background: #2589ff;
  color: #ffffff;
  border-color: #2589ff;
  box-shadow: 0 3px 10px rgba(37, 137, 255, 0.28);
}

.omni-filter-chip .chip-count {
  background: rgba(255, 255, 255, 0.25);
  padding: 1px 6px;
  border-radius: 999px;
  font-size: 10.5px;
}

.omni-filter-chip:not(.active) .chip-count {
  background: #e2eaf2;
  color: #475569;
}

/* Body & Status Bar */
.omni-body {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.omni-status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 24px;
  background: #f8fafc;
  border-bottom: 1px solid #e2eaf2;
  font-size: 12px;
  font-style: italic;
  color: #64748b;
}

[data-theme="dark"] .omni-status-bar {
  background: #0f1830;
  border-color: #1f325e;
  color: #94a3b8;
}

.omni-semantic-indicator {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: #eaf3fe;
  color: #2589ff;
  padding: 2px 9px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  border: 1px solid #c8e1fd;
  animation: pulseAi 1.5s infinite;
}

@keyframes pulseAi {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

/* Results List */
.omni-results-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px 14px;
}

.omni-empty-state {
  padding: 44px 20px;
  text-align: center;
}

.omni-empty-icon {
  font-size: 36px;
  margin-bottom: 10px;
}

.omni-empty-title {
  font-size: 16px;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 6px;
}

[data-theme="dark"] .omni-empty-title {
  color: #f8fafc;
}

.omni-empty-desc {
  font-size: 13px;
  color: #64748b;
  max-width: 440px;
  margin: 0 auto;
  line-height: 1.5;
  font-style: italic;
}

/* Result Item Card */
.omni-result-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px 16px;
  margin: 4px 0;
  border-radius: 16px;
  border: 1.5px solid transparent;
  background: #ffffff;
  cursor: pointer;
  transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1);
}

[data-theme="dark"] .omni-result-item {
  background: #111c38;
}

.omni-result-item:hover,
.omni-result-item.is-selected {
  background: #f0f7ff;
  border-color: #c8e1fd;
  transform: translateX(3px);
  box-shadow: 0 4px 16px rgba(37, 137, 255, 0.08);
}

[data-theme="dark"] .omni-result-item:hover,
[data-theme="dark"] .omni-result-item.is-selected {
  background: #172a50;
  border-color: #2e4a87;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.4);
}

.omni-item-avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: linear-gradient(135deg, #2589ff 0%, #4facfe 100%);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 14px;
  flex-shrink: 0;
  box-shadow: 0 3px 10px rgba(37, 137, 255, 0.25);
}

.omni-item-content {
  flex: 1;
  min-width: 0;
}

.omni-item-top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 3px;
  flex-wrap: wrap;
}

.omni-item-name {
  font-size: 15px;
  font-weight: 700;
  color: #1e293b;
}

[data-theme="dark"] .omni-item-name {
  color: #f8fafc;
}

.omni-item-curp-badge {
  background: #eaf3fe;
  color: #1b6fd1;
  font-family: monospace;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 6px;
  border: 1px solid #c8e1fd;
}

[data-theme="dark"] .omni-item-curp-badge {
  background: #1a2d58;
  color: #38bdf8;
  border-color: #25467e;
}

.omni-ai-badge {
  background: linear-gradient(90deg, #10b981 0%, #059669 100%);
  color: #ffffff;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 999px;
  box-shadow: 0 2px 6px rgba(16, 185, 129, 0.25);
}

.omni-item-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #64748b;
  margin-bottom: 4px;
  flex-wrap: wrap;
}

.omni-allergy-chip {
  background: #fff1f2;
  color: #e11d48;
  border: 1px solid #fecdd3;
  padding: 1px 7px;
  border-radius: 999px;
  font-size: 10.5px;
  font-weight: 600;
}

.omni-item-diagnosis {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #475569;
  line-height: 1.4;
}

[data-theme="dark"] .omni-item-diagnosis {
  color: #94a3b8;
}

.omni-cie10-pill {
  background: #2589ff;
  color: #ffffff;
  font-weight: 700;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 5px;
  flex-shrink: 0;
}

.omni-diagnosis-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.omni-highlight {
  background: #fef08a;
  color: #854d0e;
  font-weight: 700;
  border-radius: 2px;
  padding: 0 2px;
}

[data-theme="dark"] .omni-highlight {
  background: #854d0e;
  color: #fef08a;
}

/* Action Buttons */
.omni-item-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.omni-action-btn {
  background: #f4f7fb;
  border: 1px solid #e2eaf2;
  color: #475569;
  font-size: 11.5px;
  font-weight: 600;
  padding: 6px 12px;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

[data-theme="dark"] .omni-action-btn {
  background: #152244;
  border-color: #1f325e;
  color: #94a3b8;
}

.omni-action-btn:hover {
  background: #eaf3fe;
  color: #2589ff;
  border-color: #c8e1fd;
}

.omni-action-btn.primary {
  background: #2589ff;
  color: #ffffff;
  border-color: #2589ff;
  box-shadow: 0 2px 8px rgba(37, 137, 255, 0.25);
}

.omni-action-btn.primary:hover {
  background: #1b6fd1;
}

/* Footer Hints */
.omni-footer {
  padding: 10px 22px;
  background: #f8fafc;
  border-top: 1px solid #e2eaf2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11.5px;
  color: #64748b;
}

[data-theme="dark"] .omni-footer {
  background: #0b1326;
  border-color: #1f325e;
  color: #94a3b8;
}

.omni-footer-hints {
  display: flex;
  gap: 14px;
}

.omni-footer-hints kbd {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  padding: 1px 5px;
  font-size: 10px;
  color: #475569;
  font-family: monospace;
}

[data-theme="dark"] .omni-footer-hints kbd {
  background: #172a50;
  border-color: #2e4a87;
  color: #cbd5e1;
}

/* ==========================================================================
   PREMIUM SEARCHABLE COMBOBOX (REEMPLAZO DEL SELECT NATIVO)
   ========================================================================== */

.premium-combobox-wrapper {
  position: relative;
  display: inline-block;
  min-width: 340px;
}

.combobox-trigger-btn {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 12px;
  background: #ffffff;
  border: 1.5px solid #cde0f1;
  border-radius: 999px;
  padding: 7px 16px 7px 10px;
  cursor: pointer;
  text-align: left;
  transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 2px 8px rgba(37, 137, 255, 0.06);
}

[data-theme="dark"] .combobox-trigger-btn {
  background: #152244;
  border-color: #25467e;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.combobox-trigger-btn:hover {
  border-color: #2589ff;
  background: #f8fafc;
  box-shadow: 0 4px 14px rgba(37, 137, 255, 0.12);
}

[data-theme="dark"] .combobox-trigger-btn:hover {
  background: #1a2a52;
  border-color: #38bdf8;
}

.combobox-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: linear-gradient(135deg, #2589ff 0%, #4facfe 100%);
  color: #ffffff;
  font-weight: 700;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.combobox-label-group {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.combobox-name {
  font-size: 13.5px;
  font-weight: 700;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

[data-theme="dark"] .combobox-name {
  color: #f8fafc;
}

.combobox-curp {
  font-size: 11px;
  font-family: monospace;
  color: #64748b;
  letter-spacing: 0.02em;
}

[data-theme="dark"] .combobox-curp {
  color: #94a3b8;
}

.combobox-chevron {
  color: #2589ff;
  flex-shrink: 0;
  transition: transform 0.2s ease;
}

.combobox-trigger-btn[aria-expanded="true"] .combobox-chevron {
  transform: rotate(180deg);
}

/* Combobox Dropdown Popover */
.combobox-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  width: 100%;
  min-width: 360px;
  background: #ffffff;
  border: 1.5px solid #cde0f1;
  border-radius: 18px;
  box-shadow: 0 16px 40px rgba(37, 137, 255, 0.18), 0 4px 12px rgba(0, 0, 0, 0.06);
  z-index: 9999;
  overflow: hidden;
  animation: comboboxOpen 0.16s ease-out;
}

[data-theme="dark"] .combobox-dropdown {
  background: #111c38;
  border-color: #25467e;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6);
}

@keyframes comboboxOpen {
  from { opacity: 0; transform: translateY(-6px); }
  to { opacity: 1; transform: translateY(0); }
}

.combobox-search-box {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: #f8fafc;
  border-bottom: 1px solid #e2eaf2;
}

[data-theme="dark"] .combobox-search-box {
  background: #152244;
  border-color: #1f325e;
}

.combobox-search-box svg {
  color: #2589ff;
}

.combobox-search-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 13px;
  font-family: inherit;
  color: #1e293b;
  outline: none;
}

[data-theme="dark"] .combobox-search-input {
  color: #f8fafc;
}

.combobox-search-input::placeholder {
  color: #94a3b8;
  font-style: italic;
}

.combobox-items-container {
  max-height: 280px;
  overflow-y: auto;
  padding: 6px;
}

.combobox-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.combobox-item:hover,
.combobox-item.is-selected {
  background: #eaf3fe;
}

[data-theme="dark"] .combobox-item:hover,
[data-theme="dark"] .combobox-item.is-selected {
  background: #172a50;
}

.combobox-item-avatar {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: #2589ff;
  color: #ffffff;
  font-weight: 700;
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.combobox-item-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.combobox-item-name {
  font-size: 13px;
  font-weight: 700;
  color: #1e293b;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

[data-theme="dark"] .combobox-item-name {
  color: #f8fafc;
}

.combobox-item-meta {
  font-size: 11px;
  font-family: monospace;
  color: #64748b;
}

[data-theme="dark"] .combobox-item-meta {
  color: #94a3b8;
}

.combobox-item-disease {
  font-size: 11px;
  font-style: italic;
  color: #2589ff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.combobox-checkmark {
  color: #2589ff;
  font-weight: 800;
  font-size: 14px;
}

.combobox-footer {
  padding: 8px 12px;
  background: #f8fafc;
  border-top: 1px solid #e2eaf2;
  text-align: center;
}

[data-theme="dark"] .combobox-footer {
  background: #0f1830;
  border-color: #1f325e;
}

.combobox-open-spotlight-link {
  background: none;
  border: none;
  color: #2589ff;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: all 0.15s ease;
}

.combobox-open-spotlight-link:hover {
  text-decoration: underline;
  background: #eaf3fe;
}
"""

def apply():
    for root in ROOTS:
        css_path = os.path.join(root, "frontend", "style.css")
        if not os.path.exists(css_path):
            continue
        with open(css_path, "r", encoding="utf-8") as f:
            content = f.read()
        marker = "/* ==========================================================================\n   PREMIUM SEARCH & COMMAND PALETTE (OMNI-SEARCH SPOTLIGHT)"
        if marker in content:
            idx = content.find(marker)
            content = content[:idx] + PREMIUM_SEARCH_CSS.strip() + "\n"
        else:
            content = content + "\n\n" + PREMIUM_SEARCH_CSS.strip() + "\n"
        with open(css_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"Updated CSS with Premium Search styles: {css_path}")

if __name__ == "__main__":
    apply()
