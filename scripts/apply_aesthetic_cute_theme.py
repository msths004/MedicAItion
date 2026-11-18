# -*- coding: utf-8 -*-
"""
apply_aesthetic_cute_theme.py
Aplica una paleta de colores linda, fresca y estética ("Aesthetic Pastel Serenity & Friendly Clinical")
a MedicAItion, cuidando:
- Colores amigables y cálidos pero profesionales: Celeste cielo (#0ea5e9 / #38bdf8), Menta suave (#10b981 / #ecfdf5),
  Lavanda pastel (#8b5cf6 / #f5f3ff) y toques Coral suave (#f43f5e / #fff1f2).
- Tarjetas blancas inmaculadas con esquinas suaves (radius: 16px), micro-interacciones hover y sombras de ensueño.
- Topbar y Sidebar con estética moderna estilo Apple Health / Med+ dashboard.
- Botones con hermosos degradados sutiles y estados activos vibrantes.
- Realce tierno y carismático para Dr. Oso y el asistente Pulso IA.
"""

import os

CSS_FILE = os.path.join(os.path.dirname(__file__), "..", "frontend", "style.css")

AESTHETIC_THEME_CSS = """

/* ==========================================================================
   AESTHETIC PASTEL SERENITY & FRIENDLY CLINICAL PALETTE ("COLOR LINDO")
   - Paleta amigable, serena y luminosa para el software mÃ©dico
   - Celeste Cielo, Menta Fresca, Lavanda Inteligente y Coral Suave
   - Tarjetas redondeadas, sombras etÃ©reas y micro-interacciones suaves
   ========================================================================== */

:root,
[data-theme="light"] {
  --bg-base: #f6f9fc !important;
  --bg-panel: #ffffff !important;
  --bg-card: #ffffff !important;
  --bg-input: #f8fafc !important;
  --bg-hover: #f0f7ff !important;

  --border: #e2e8f0 !important;
  --border-accent: #c7ddf5 !important;
  --border-focus: #0ea5e9 !important;

  --text-primary: #0f172a !important;
  --text-secondary: #475569 !important;
  --text-muted: #94a3b8 !important;

  /* Colores lindos y amigables */
  --cute-sky-primary: #0284c7 !important;
  --cute-sky-soft: #e0f2fe !important;
  --cute-sky-gradient: linear-gradient(135deg, #0ea5e9 0%, #0284c7 100%) !important;

  --cute-mint-primary: #059669 !important;
  --cute-mint-soft: #d1fae5 !important;
  --cute-mint-gradient: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;

  --cute-lavender-primary: #7c3aed !important;
  --cute-lavender-soft: #ede9fe !important;
  --cute-lavender-gradient: linear-gradient(135deg, #8b5cf6 0%, #6366f1 100%) !important;

  --cute-coral-primary: #e11d48 !important;
  --cute-coral-soft: #ffe4e6 !important;

  --cute-amber-primary: #d97706 !important;
  --cute-amber-soft: #fef3c7 !important;

  --shadow-cute-card: 0 10px 25px -5px rgba(14, 165, 233, 0.07), 0 4px 10px -2px rgba(15, 23, 42, 0.03) !important;
  --shadow-cute-hover: 0 16px 36px -4px rgba(14, 165, 233, 0.15), 0 6px 12px -2px rgba(15, 23, 42, 0.04) !important;
  --shadow-cute-btn: 0 4px 14px rgba(14, 165, 233, 0.28) !important;
}

[data-theme="dark"] {
  --bg-base: #090e1a !important;
  --bg-panel: #10172a !important;
  --bg-card: #141e34 !important;
  --bg-input: #1a2744 !important;
  --bg-hover: #213256 !important;

  --border: #1e2e4f !important;
  --border-accent: #2e4472 !important;
  --border-focus: #38bdf8 !important;

  --text-primary: #f8fafc !important;
  --text-secondary: #94a3b8 !important;
  --text-muted: #64748b !important;

  --cute-sky-primary: #38bdf8 !important;
  --cute-sky-soft: #172847 !important;
  --cute-sky-gradient: linear-gradient(135deg, #0284c7 0%, #38bdf8 100%) !important;

  --cute-mint-primary: #34d399 !important;
  --cute-mint-soft: #113328 !important;

  --cute-lavender-primary: #a78bfa !important;
  --cute-lavender-soft: #271e44 !important;

  --shadow-cute-card: 0 10px 28px rgba(0, 0, 0, 0.45) !important;
  --shadow-cute-hover: 0 16px 38px rgba(0, 0, 0, 0.6) !important;
  --shadow-cute-btn: 0 4px 16px rgba(56, 189, 248, 0.25) !important;
}

/* 1. TOPBAR & HEADER ESTÃ‰TICO */
.topbar {
  background: rgba(255, 255, 255, 0.88) !important;
  backdrop-filter: blur(14px) !important;
  -webkit-backdrop-filter: blur(14px) !important;
  border-bottom: 1.5px solid var(--border) !important;
  box-shadow: 0 2px 12px rgba(14, 165, 233, 0.04) !important;
  transition: all 0.25s ease !important;
}

[data-theme="dark"] .topbar {
  background: rgba(16, 23, 42, 0.92) !important;
  border-bottom: 1.5px solid var(--border) !important;
}

/* LÃ­nea de acento multicolor sutil en la parte superior del encabezado */
.topbar::before {
  content: "" !important;
  position: absolute !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  height: 3px !important;
  background: linear-gradient(90deg, #38bdf8 0%, #818cf8 50%, #34d399 100%) !important;
  z-index: 101 !important;
}

/* 2. SIDEBAR LIMPIO Y AMISTOSO */
.app-sidebar {
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%) !important;
  border-right: 1.5px solid var(--border) !important;
  box-shadow: 2px 0 14px rgba(14, 165, 233, 0.03) !important;
}

[data-theme="dark"] .app-sidebar {
  background: linear-gradient(180deg, #10172a 0%, #0d1424 100%) !important;
  border-right: 1.5px solid var(--border) !important;
}

.sidebar-nav-btn {
  border-radius: 12px !important;
  font-weight: 500 !important;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

.sidebar-nav-btn:hover {
  background: var(--cute-sky-soft) !important;
  color: var(--cute-sky-primary) !important;
  transform: translateX(3px) !important;
}

.sidebar-nav-btn.active {
  background: linear-gradient(135deg, #e0f2fe 0%, #f0fdf4 100%) !important;
  color: var(--cute-sky-primary) !important;
  font-weight: 700 !important;
  box-shadow: 0 4px 12px rgba(14, 165, 233, 0.12) !important;
  border-left: 3.5px solid #0ea5e9 !important;
}

[data-theme="dark"] .sidebar-nav-btn.active {
  background: linear-gradient(135deg, #172847 0%, #15273f 100%) !important;
  color: #38bdf8 !important;
  border-left: 3.5px solid #38bdf8 !important;
}

/* 3. PÃLDORAS Y BADGES MODERNAS */
.topbar-role-pill {
  background: linear-gradient(135deg, #e0f2fe 0%, #ede9fe 100%) !important;
  border: 1px solid #bae6fd !important;
  color: #0369a1 !important;
  border-radius: 20px !important;
  padding: 6px 14px !important;
  font-weight: 600 !important;
  box-shadow: 0 2px 6px rgba(14, 165, 233, 0.08) !important;
  transition: all 0.2s ease !important;
}

.topbar-role-pill:hover {
  transform: translateY(-1px) !important;
  box-shadow: 0 4px 10px rgba(14, 165, 233, 0.15) !important;
}

.topbar-theme-pill {
  background: #f1f5f9 !important;
  border: 1px solid #e2e8f0 !important;
  border-radius: 20px !important;
  transition: all 0.2s ease !important;
}

.topbar-theme-pill:hover {
  background: #e2e8f0 !important;
  transform: rotate(15deg) !important;
}

/* 4. TARJETAS CLÃNICAS Y PANELES (AIRY & CLEAN) */
.clinical-split-panel,
.panel-patient-vitals,
.panel-consulta-col2,
.panel-consulta-col3,
.patient-card,
.kpi-card,
.summary-card {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: 18px !important;
  box-shadow: var(--shadow-cute-card) !important;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease !important;
}

.patient-card:hover,
.kpi-card:hover {
  transform: translateY(-3px) !important;
  box-shadow: var(--shadow-cute-hover) !important;
  border-color: var(--border-accent) !important;
}

/* 5. BOTONES DE ACCIÃ“N CON ESTILO LINDO */
.btn-primary,
.btn-mod-consult,
.btn-register-patient-modern {
  background: var(--cute-sky-gradient) !important;
  color: #ffffff !important;
  border: none !important;
  border-radius: 12px !important;
  font-weight: 600 !important;
  padding: 9px 18px !important;
  box-shadow: var(--shadow-cute-btn) !important;
  cursor: pointer !important;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
}

.btn-primary:hover,
.btn-mod-consult:hover,
.btn-register-patient-modern:hover {
  transform: translateY(-2px) !important;
  box-shadow: 0 6px 20px rgba(14, 165, 233, 0.4) !important;
  filter: brightness(1.05) !important;
}

.btn-secondary,
.btn-mod-profile {
  background: #ffffff !important;
  border: 1.5px solid var(--border) !important;
  color: var(--text-secondary) !important;
  border-radius: 12px !important;
  font-weight: 600 !important;
  padding: 8px 16px !important;
  cursor: pointer !important;
  transition: all 0.2s ease !important;
}

.btn-secondary:hover,
.btn-mod-profile:hover {
  background: var(--bg-hover) !important;
  color: var(--text-primary) !important;
  border-color: var(--border-focus) !important;
  transform: translateY(-1px) !important;
}

/* 6. CHIPS Y BADGES DE SIGNOS VITALES ESTÃ‰TICOS */
.vital-badge-fc {
  background: #ffe4e6 !important;
  color: #e11d48 !important;
  border: 1px solid #fecdd3 !important;
  border-radius: 10px !important;
  padding: 4px 10px !important;
  font-weight: 700 !important;
}

.vital-badge-ta {
  background: #e0f2fe !important;
  color: #0284c7 !important;
  border: 1px solid #bae6fd !important;
  border-radius: 10px !important;
  padding: 4px 10px !important;
  font-weight: 700 !important;
}

.vital-badge-spo2 {
  background: #d1fae5 !important;
  color: #059669 !important;
  border: 1px solid #a7f3d0 !important;
  border-radius: 10px !important;
  padding: 4px 10px !important;
  font-weight: 700 !important;
}

.vital-badge-temp {
  background: #fef3c7 !important;
  color: #d97706 !important;
  border: 1px solid #fde68a !important;
  border-radius: 10px !important;
  padding: 4px 10px !important;
  font-weight: 700 !important;
}

/* 7. DR. OSO KAWAII & ASISTENTE PULSO IA */
.pulso-fab-btn {
  box-shadow: 0 8px 24px rgba(14, 165, 233, 0.35), 0 0 0 4px rgba(255, 255, 255, 0.8) !important;
  border-radius: 50% !important;
  transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.25s ease !important;
}

.pulso-fab-btn:hover {
  transform: scale(1.08) !important;
  box-shadow: 0 12px 30px rgba(14, 165, 233, 0.45), 0 0 0 6px rgba(56, 189, 248, 0.25) !important;
}

.pulso-chat-panel {
  border-radius: 24px !important;
  box-shadow: 0 20px 50px rgba(14, 165, 233, 0.2) !important;
  border: 1.5px solid var(--border-accent) !important;
}

.pulso-chat-header {
  background: linear-gradient(135deg, #0284c7 0%, #0ea5e9 50%, #38bdf8 100%) !important;
  color: #ffffff !important;
  border-top-left-radius: 22px !important;
  border-top-right-radius: 22px !important;
}

/* 8. INPUTS Y TEXTAREAS FLUIDOS Y SUAVES */
input[type="text"],
input[type="search"],
input[type="number"],
input[type="date"],
select,
textarea {
  border-radius: 12px !important;
  border: 1.5px solid var(--border) !important;
  background: var(--bg-input) !important;
  color: var(--text-primary) !important;
  padding: 9px 14px !important;
  font-size: 13.5px !important;
  transition: border-color 0.2s ease, box-shadow 0.2s ease !important;
}

input:focus,
select:focus,
textarea:focus {
  outline: none !important;
  border-color: #0ea5e9 !important;
  box-shadow: 0 0 0 4px rgba(14, 165, 233, 0.15) !important;
  background: #ffffff !important;
}

[data-theme="dark"] input:focus,
[data-theme="dark"] select:focus,
[data-theme="dark"] textarea:focus {
  background: #141e34 !important;
}
"""

def apply_theme():
    if not os.path.exists(CSS_FILE):
        print(f"No se encontrÃ³ {CSS_FILE}")
        return
    with open(CSS_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    
    tag = "/* === AESTHETIC PASTEL SERENITY CLINICAL PALETTE"
    if tag in content:
        print("El tema ya estaba aplicado previamente.")
        return

    with open(CSS_FILE, "a", encoding="utf-8") as f:
        f.write("\n\n" + AESTHETIC_THEME_CSS)
    print("Â¡Tema lindo y estÃ©tico aplicado correctamente a style.css!")

if __name__ == "__main__":
    apply_theme()
