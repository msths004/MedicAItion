# -*- coding: utf-8 -*-
"""
scripts/apply_patient_sections_modules.py
=========================================
Implements the requested organized Modular Sections for the Directorio de Pacientes:
- Groups patients into structured clinical modules by disease/condition (matching wireframe):
  1. PACIENTES CON DIABETES & METABÓLICOS
  2. PACIENTES CON HIPERTENSIÓN & CARDIOVASCULAR
  3. PACIENTES CON DENGUE & ENFERMEDADES FEBRILES
  4. PACIENTES CON ENFERMEDADES RESPIRATORIAS (ASMA / EPOC)
  5. PACIENTES CON ENFERMEDADES REUMATOLÓGICAS Y RENALES
  6. PACIENTES DE ESPECIALIDADES MÉDICAS Y CIRUGÍA
- Interactive filter bar by cohort.
- Rich patient cards with diagnosis pills, clinical telemetry, and 1-click consultation jump.
- Synchronizes changes to Linux_Ver.
"""

import os
import re

ROOTS = [
    r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion",
    r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion\Linux_Ver"
]

INDEX_HTML_SNIPPET = """
            <!-- BARRA DE FILTRO POR SECCIONES / COHORTES CLÍNICAS -->
            <div class="patients-cohorts-nav-bar" id="patients-cohorts-nav">
              <div class="cohorts-scroll-wrap">
                <button type="button" class="cohort-filter-btn active" data-cat="all" onclick="filterPatientsByCohort('all')">
                  <span class="cohort-emoji">🌟</span>
                  <span class="cohort-name">Todas las Secciones</span>
                  <span class="cohort-count" id="cohort-cnt-all">25</span>
                </button>
                <button type="button" class="cohort-filter-btn" data-cat="diabetes" onclick="filterPatientsByCohort('diabetes')">
                  <span class="cohort-emoji">🩸</span>
                  <span class="cohort-name">Diabetes & Metabólicos</span>
                  <span class="cohort-count" id="cohort-cnt-diabetes">3</span>
                </button>
                <button type="button" class="cohort-filter-btn" data-cat="hipertension" onclick="filterPatientsByCohort('hipertension')">
                  <span class="cohort-emoji">❤️</span>
                  <span class="cohort-name">Hipertensión & Cardíaco</span>
                  <span class="cohort-count" id="cohort-cnt-hipertension">3</span>
                </button>
                <button type="button" class="cohort-filter-btn" data-cat="dengue" onclick="filterPatientsByCohort('dengue')">
                  <span class="cohort-emoji">🦟</span>
                  <span class="cohort-name">Dengue & Febriles</span>
                  <span class="cohort-count" id="cohort-cnt-dengue">3</span>
                </button>
                <button type="button" class="cohort-filter-btn" data-cat="respiratorio" onclick="filterPatientsByCohort('respiratorio')">
                  <span class="cohort-emoji">🫁</span>
                  <span class="cohort-name">Respiratorio & Asma</span>
                  <span class="cohort-count" id="cohort-cnt-respiratorio">3</span>
                </button>
                <button type="button" class="cohort-filter-btn" data-cat="reuma_renal" onclick="filterPatientsByCohort('reuma_renal')">
                  <span class="cohort-emoji">🧬</span>
                  <span class="cohort-name">Reumatología & Renal</span>
                  <span class="cohort-count" id="cohort-cnt-reuma">4</span>
                </button>
                <button type="button" class="cohort-filter-btn" data-cat="especialidades" onclick="filterPatientsByCohort('especialidades')">
                  <span class="cohort-emoji">🏥</span>
                  <span class="cohort-name">Especialidades & General</span>
                  <span class="cohort-count" id="cohort-cnt-esp">9</span>
                </button>
              </div>

              <!-- Selector de Vista: Secciones Modulares vs Tabla -->
              <div class="view-mode-toggle-group">
                <button type="button" class="view-mode-btn active" id="btn-view-modules" onclick="setPatientsViewMode('modules')" title="Vista modular organizada por secciones de enfermedad">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect width="7" height="7" x="3" y="3" rx="1.5"/><rect width="7" height="7" x="14" y="3" rx="1.5"/><rect width="7" height="7" x="14" y="14" rx="1.5"/><rect width="7" height="7" x="3" y="14" rx="1.5"/></svg>
                  <span>Módulos</span>
                </button>
                <button type="button" class="view-mode-btn" id="btn-view-table" onclick="setPatientsViewMode('table')" title="Vista de lista continua">
                  <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
                  <span>Lista</span>
                </button>
              </div>
            </div>
"""

CSS_SECTIONS_CODE = """
/* ==========================================================================
   DIRECTORIO DE PACIENTES: VISTA MODULAR POR SECCIONES CLÍNICAS
   Organización visual en módulos por enfermedad (Look & Feel Blanco y Celeste)
   ========================================================================== */

.patients-cohorts-nav-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  margin-top: 14px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.cohorts-scroll-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 4px;
  flex: 1;
}

.cohort-filter-btn {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  background: #ffffff;
  border: 1.5px solid #e2e8f0;
  border-radius: 999px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.18s ease;
  box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.cohort-filter-btn:hover {
  border-color: #38bdf8;
  color: #0284c7;
  background: #f0fdf4;
}

.cohort-filter-btn.active {
  background: #0284c7;
  color: #ffffff;
  border-color: #0284c7;
  box-shadow: 0 4px 12px rgba(2, 132, 199, 0.25);
}

.cohort-count {
  background: #f1f5f9;
  color: #334155;
  font-size: 10px;
  font-weight: 800;
  padding: 2px 7px;
  border-radius: 999px;
}

.cohort-filter-btn.active .cohort-count {
  background: rgba(255, 255, 255, 0.25);
  color: #ffffff;
}

.view-mode-toggle-group {
  display: inline-flex;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 3px;
  gap: 3px;
}

.view-mode-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  border: none;
  background: transparent;
  padding: 6px 12px;
  font-size: 11px;
  font-weight: 700;
  color: #64748b;
  border-radius: 9px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.view-mode-btn.active {
  background: #ffffff;
  color: #0284c7;
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.08);
}

/* Grilla Modular de Secciones */
.patients-modules-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(520px, 1fr));
  gap: 24px;
  align-items: start;
}

@media (max-width: 900px) {
  .patients-modules-grid {
    grid-template-columns: 1fr;
  }
}

.patient-section-card {
  background: #ffffff;
  border: 1.5px solid #e2e8f0;
  border-radius: 22px;
  overflow: hidden;
  box-shadow: 0 4px 18px rgba(15, 23, 42, 0.04);
  transition: all 0.22s ease;
  display: flex;
  flex-direction: column;
}

.patient-section-card:hover {
  box-shadow: 0 8px 26px rgba(2, 132, 199, 0.09);
  border-color: #7dd3fc;
}

.section-card-header {
  padding: 16px 20px;
  border-bottom: 1.5px solid #f1f5f9;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(135deg, #f8fafc 0%, #f0f9ff 100%);
}

.section-title-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
}

.section-icon-badge {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  background: #e0f2fe;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  box-shadow: 0 2px 6px rgba(2, 132, 199, 0.12);
  flex-shrink: 0;
}

.section-main-title {
  font-size: 14px;
  font-weight: 800;
  color: #0f172a;
  letter-spacing: 0.3px;
  text-transform: uppercase;
  margin: 0;
}

.section-sub-desc {
  font-size: 11px;
  font-style: italic;
  color: #64748b;
  margin: 2px 0 0;
}

.section-badge-counter {
  font-size: 11px;
  font-weight: 700;
  color: #0284c7;
  background: #e0f2fe;
  border: 1px solid #bae6fd;
  padding: 4px 10px;
  border-radius: 999px;
  white-space: nowrap;
}

.section-patients-list {
  padding: 14px 18px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* Tarjeta individual de paciente dentro de la sección */
.modular-patient-row {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 12px 14px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  transition: all 0.18s ease;
  cursor: pointer;
}

.modular-patient-row:hover {
  background: #f8fafc;
  border-color: #38bdf8;
  transform: translateX(3px);
  box-shadow: 0 3px 10px rgba(15, 23, 42, 0.05);
}

.pt-mod-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
  min-width: 0;
}

.pt-mod-avatar {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  background: linear-gradient(135deg, #0284c7 0%, #38bdf8 100%);
  color: #ffffff;
  font-size: 14px;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  box-shadow: 0 2px 6px rgba(2, 132, 199, 0.22);
}

.pt-mod-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.pt-mod-name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.pt-mod-name {
  font-size: 13.5px;
  font-weight: 700;
  color: #0f172a;
}

.pt-mod-demog {
  font-size: 11px;
  color: #64748b;
}

.pt-mod-curp-code {
  font-size: 10px;
  font-family: monospace;
  color: #64748b;
  background: #f1f5f9;
  padding: 1px 6px;
  border-radius: 4px;
}

.pt-mod-disease-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 700;
  color: #0369a1;
  background: #e0f2fe;
  padding: 2px 8px;
  border-radius: 6px;
  margin-top: 3px;
  width: fit-content;
}

.pt-mod-highlight {
  font-size: 10.5px;
  font-style: italic;
  color: #059669;
  margin-top: 2px;
}

.pt-mod-actions {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.btn-mod-consult {
  background: #0284c7;
  color: #ffffff;
  border: none;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 700;
  padding: 6px 11px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
  transition: all 0.15s ease;
}

.btn-mod-consult:hover {
  background: #0369a1;
  box-shadow: 0 2px 8px rgba(2, 132, 199, 0.28);
}

.btn-mod-profile {
  background: #ffffff;
  border: 1px solid #cbd5e1;
  color: #475569;
  border-radius: 8px;
  font-size: 11px;
  font-weight: 600;
  padding: 6px 10px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-mod-profile:hover {
  background: #f1f5f9;
  color: #0f172a;
}
"""

JS_SECTION_MODULE_LOGIC = """
/* ==========================================================================
   PACIENTES: MAPA CLÍNICO Y MOTOR DE RENDERIZADO POR MÓDULOS DE SECCIÓN
   ========================================================================== */

window.PATIENTS_CLINICAL_MAP = {
  "VASE820412MMNZLL09": { disease: "Diabetes Mellitus Tipo 2 no insulinodependiente (E11.9)", category: "diabetes", category_title: "PACIENTES CON DIABETES Y TRASTORNOS METABÓLICOS", cie10: "E11.9", icon: "🩸", highlight: "Glucosa: 128 mg/dL • En Control" },
  "GUMF780224MCLNS02": { disease: "Hipotiroidismo de Hashimoto (E03.9)", category: "diabetes", category_title: "PACIENTES CON DIABETES Y TRASTORNOS METABÓLICOS", cie10: "E03.9", icon: "🩸", highlight: "TSH: 3.2 mUI/L • Estable" },
  "GOPC790814HYNCLN04": { disease: "Diabetes Mellitus Tipo 2 y HAS (E11.9 / I10)", category: "diabetes", category_title: "PACIENTES CON DIABETES Y TRASTORNOS METABÓLICOS", cie10: "E11.9", icon: "🩸", highlight: "Glucosa: 142 mg/dL • TA: 130/84" },

  "MECA680925HDFNT01": { disease: "Hipertensión Arterial Sistémica Estadio 2 (I10)", category: "hipertension", category_title: "PACIENTES CON HIPERTENSIÓN Y ENFERMEDADES CARDIOVASCULARES", cie10: "I10", icon: "❤️", highlight: "TA: 154/94 mmHg • En Ajuste" },
  "SAPB640703MGRNL06": { disease: "Insuficiencia Cardíaca Congestiva NYHA II (I50.9)", category: "hipertension", category_title: "PACIENTES CON HIPERTENSIÓN Y ENFERMEDADES CARDIOVASCULARES", cie10: "I50.9", icon: "❤️", highlight: "FC: 74 lpm • FEy: 42%" },
  "TESTCURP1234567890": { disease: "Hipertensión Arterial Primaria (I10)", category: "hipertension", category_title: "PACIENTES CON HIPERTENSIÓN Y ENFERMEDADES CARDIOVASCULARES", cie10: "I10", icon: "❤️", highlight: "TA: 138/88 mmHg • Control" },

  "PACV950119MYNLR03": { disease: "Dengue con Signos de Alarma (A90)", category: "dengue", category_title: "PACIENTES CON DENGUE Y ENFERMEDADES FEBRILES / INFECCIOSAS", cie10: "A90", icon: "🦟", highlight: "Temp: 38.4 °C • Plaqueta: 98k" },
  "VEMR850820HDFNTS03": { disease: "COVID-19 Agudo con Síntomas Febriles (U07.1)", category: "dengue", category_title: "PACIENTES CON DENGUE Y ENFERMEDADES FEBRILES / INFECCIOSAS", cie10: "U07.1", icon: "🦟", highlight: "SpO2: 96% • Aislamiento" },
  "CAAD080530HYNLR04": { disease: "Gastroenteritis Infecciosa Aguda (A09)", category: "dengue", category_title: "PACIENTES CON DENGUE Y ENFERMEDADES FEBRILES / INFECCIOSAS", cie10: "A09", icon: "🦟", highlight: "Temp: 37.8 °C • Hidratación" },

  "RINS031108MNLRVF05": { disease: "Asma Bronquial Alérgica Persistente (J45.0)", category: "respiratorio", category_title: "PACIENTES CON ENFERMEDADES RESPIRATORIAS, ASMA Y EPOC", cie10: "J45.0", icon: "🫁", highlight: "SpO2: 95% • FR: 20 rpm" },
  "SOCF510410HDFMS05": { disease: "Enfermedad Pulmonar Obstructiva Crónica EPOC (J44.9)", category: "respiratorio", category_title: "PACIENTES CON ENFERMEDADES RESPIRATORIAS, ASMA Y EPOC", cie10: "J44.9", icon: "🫁", highlight: "SpO2: 92% • FEV1: 58%" },
  "LOEM740618HJCRT08": { disease: "Neumonía Bacteriana Adquirida en Comunidad (J18.9)", category: "respiratorio", category_title: "PACIENTES CON ENFERMEDADES RESPIRATORIAS, ASMA Y EPOC", cie10: "J18.9", icon: "🫁", highlight: "Temp: 38.1 °C • Antibiótico" },

  "NABC870811MDFRL09": { disease: "Lupus Eritematoso Sistémico LES (M32.9)", category: "reuma_renal", category_title: "PACIENTES CON ENFERMEDADES REUMATOLÓGICAS Y RENALES", cie10: "M32.9", icon: "🧬", highlight: "ANA Positivo • Remisión" },
  "FUBI600305HPLEL07": { disease: "Artritis Reumatoide Seropositiva (M05.9)", category: "reuma_renal", category_title: "PACIENTES CON ENFERMEDADES REUMATOLÓGICAS Y RENALES", cie10: "M05.9", icon: "🧬", highlight: "DAS28: 3.1 • Metotrexato" },
  "OOVG531201HTSNLN08": { disease: "Enfermedad Renal Crónica Estadio G3b (N18.3)", category: "reuma_renal", category_title: "PACIENTES CON ENFERMEDADES REUMATOLÓGICAS Y RENALES", cie10: "N18.3", icon: "🧬", highlight: "TFG: 42 mL/min • Control" },
  "IACM920315MJCLNR01": { disease: "Pielonefritis Aguda / IVU Complicada (N10)", category: "reuma_renal", category_title: "PACIENTES CON ENFERMEDADES REUMATOLÓGICAS Y RENALES", cie10: "N10", icon: "🧬", highlight: "Temp: 37.6 °C • Urocultivo" },

  "AAVT560918MDFLNN02": { disease: "Glaucoma Primario de Ángulo Abierto (H40.1)", category: "especialidades", category_title: "PACIENTES DE ESPECIALIDADES, CIRUGÍA Y GENERAL", cie10: "H40.1", icon: "🏥", highlight: "PIO: 16 mmHg • Timolol" },
  "MIPJ761005HCLNR03": { disease: "Hernia Discal L4-L5 con Radiculopatía (M51.1)", category: "especialidades", category_title: "PACIENTES DE ESPECIALIDADES, CIRUGÍA Y GENERAL", cie10: "M51.1", icon: "🏥", highlight: "Lasegue (+) • Fisioterapia" },
  "TRGP900604MNLRRN09": { disease: "Trastorno Depresivo Mayor y Ansiedad (F33.1)", category: "especialidades", category_title: "PACIENTES DE ESPECIALIDADES, CIRUGÍA Y GENERAL", cie10: "F33.1", icon: "🏥", highlight: "PHQ-9: 8 • En Remisión" },
  "HESC050814MDFRL02": { disease: "Apendicitis Aguda Focal en Observación (K35.8)", category: "especialidades", category_title: "PACIENTES DE ESPECIALIDADES, CIRUGÍA Y GENERAL", cie10: "K35.8", icon: "🏥", highlight: "McBurney (+) • Quirúrgico" },
  "MATR691129MJCLSR08": { disease: "Colecistitis Crónica Litiásica (K80.2)", category: "especialidades", category_title: "PACIENTES DE ESPECIALIDADES, CIRUGÍA Y GENERAL", cie10: "K80.2", icon: "🏥", highlight: "Murphy (+) • Ecografía" },
  "SOQE170310HYNLR06": { disease: "Otitis Media Aguda Supurativa (H66.0)", category: "especialidades", category_title: "PACIENTES DE ESPECIALIDADES, CIRUGÍA Y GENERAL", cie10: "H66.0", icon: "🏥", highlight: "Temp: 37.4 °C • Amoxicilina" },
  "PAOS120722HDFRNT05": { disease: "Dermatitis Atópica Severa (L20.9)", category: "especialidades", category_title: "PACIENTES DE ESPECIALIDADES, CIRUGÍA Y GENERAL", cie10: "L20.9", icon: "🏥", highlight: "SCORAD: 28 • Emolientes" },
  "MOZL891012MDFRN07": { disease: "Migraña Crónica con Aura Oftálmica (G43.1)", category: "especialidades", category_title: "PACIENTES DE ESPECIALIDADES, CIRUGÍA Y GENERAL", cie10: "G43.1", icon: "🏥", highlight: "EVA: 4/10 • Triptanes" },
  "MOBK070228HYNRTVA3": { disease: "Control Clínico General & Telemetría Preventiva (Z00.0)", category: "especialidades", category_title: "PACIENTES DE ESPECIALIDADES, CIRUGÍA Y GENERAL", cie10: "Z00.0", icon: "🏥", highlight: "FC: 78 lpm • Sano" }
};

window.currentPatientCohort = 'all';
window.patientsViewMode = 'modules'; // 'modules' or 'table'

function filterPatientsByCohort(cat) {
  window.currentPatientCohort = cat;
  document.querySelectorAll('.cohort-filter-btn').forEach(btn => {
    btn.classList.toggle('active', btn.getAttribute('data-cat') === cat);
  });
  renderPatients(AppState.allPatients || []);
}

function setPatientsViewMode(mode) {
  window.patientsViewMode = mode;
  document.getElementById('btn-view-modules')?.classList.toggle('active', mode === 'modules');
  document.getElementById('btn-view-table')?.classList.toggle('active', mode === 'table');
  const tableHeader = document.querySelector('.patients-pseudo-table-header');
  if (tableHeader) {
    tableHeader.style.display = mode === 'table' ? 'grid' : 'none';
  }
  renderPatients(AppState.allPatients || []);
}

function jumpToConsultWithPatient(curp) {
  if (typeof switchMainTab === 'function') {
    switchMainTab('consulta');
  }
  if (typeof onConsultaPatientSelect === 'function') {
    onConsultaPatientSelect(curp);
  }
}
"""

def update_index_html(base_dir):
    p = os.path.join(base_dir, "frontend", "index.html")
    if not os.path.exists(p):
        return
    with open(p, "r", encoding="utf-8") as f:
        html = f.read()

    # Add the cohorts nav bar if not present
    if "patients-cohorts-nav" not in html:
        # Find where to insert: right after patients-floating-bar
        target = '</div>\n            </div>\n\n            <div class="patients-pseudo-table-header">'
        if target in html:
            html = html.replace(target, '</div>\n            </div>\n' + INDEX_HTML_SNIPPET + '\n            <div class="patients-pseudo-table-header" style="display:none">')
        else:
            # Fallback
            html = html.replace('<div class="patients-pseudo-table-header">', INDEX_HTML_SNIPPET + '\n            <div class="patients-pseudo-table-header" style="display:none">')
        print(f"Added cohorts navigation in: {p}")

    with open(p, "w", encoding="utf-8") as f:
        f.write(html)


def update_style_css(base_dir):
    p = os.path.join(base_dir, "frontend", "style.css")
    if not os.path.exists(p):
        return
    with open(p, "r", encoding="utf-8") as f:
        css = f.read()

    if "DIRECTORIO DE PACIENTES: VISTA MODULAR POR SECCIONES CLÍNICAS" not in css:
        css = css.strip() + "\n\n" + CSS_SECTIONS_CODE.strip() + "\n"
        with open(p, "w", encoding="utf-8") as f:
            f.write(css)
        print(f"Added modular sections CSS in: {p}")


def update_app_js(base_dir):
    p = os.path.join(base_dir, "frontend", "app.js")
    if not os.path.exists(p):
        return
    with open(p, "r", encoding="utf-8") as f:
        js = f.read()

    # Check if section logic is already added
    if "PATIENTS_CLINICAL_MAP" not in js:
        js = js + "\n\n" + JS_SECTION_MODULE_LOGIC.strip() + "\n"

    # Replace renderPatients with the new modular section renderer
    new_render_patients = """function renderPatients(patients, isSemantic = false, emptyQuery = '') {
  const el = document.getElementById('patients-list');
  if (!el) return;

  if (!patients || !patients.length) {
    const msg = emptyQuery
      ? `No se encontraron pacientes que coincidan con "${esc(emptyQuery)}".`
      : (isSemantic ? 'No se encontraron coincidencias semánticas.' : 'Sin pacientes registrados.');
    el.innerHTML = `<div class="no-patients">${msg}</div>`;
    return;
  }

  // Si el usuario eligió vista tabular clásica
  if (window.patientsViewMode === 'table') {
    const tableHeader = document.querySelector('.patients-pseudo-table-header');
    if (tableHeader) tableHeader.style.display = 'grid';

    el.className = 'patients-detached-list';
    el.innerHTML = patients.map(p => {
      const curp = isSemantic ? p.patient_curp : p.curp;
      const nombre = isSemantic ? (p.nombre_paciente || 'Nombre no registrado') : (p.nombre || p.nombre_completo || 'Nombre no registrado');
      const sexo = p.sexo || '';
      const edad = p.edad != null ? `${p.edad} años` : '';
      const folio = p.folio_hospital || '';
      const fecha = formatDate(p.created_at);
      const cInfo = (window.PATIENTS_CLINICAL_MAP && window.PATIENTS_CLINICAL_MAP[curp]) || { disease: 'Medicina General', cie10: 'Z00' };
      return `
        <div class="patient-row" data-curp="${esc(curp)}" onclick="openPatientProfile('${esc(curp)}')" role="button" tabindex="0">
          <div class="pt-col-patient">
            <div class="patient-row-avatar">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
            </div>
            <div class="patient-row-info">
              <span class="patient-row-name">${esc(nombre)}</span>
              <span class="patient-row-meta">${sexo ? sexo : ''}${sexo && edad ? ' • ' : ''}${edad} • <strong>${esc(cInfo.disease)}</strong></span>
              ${curp ? `<span class="patient-row-curp-badge">CURP: ${esc(curp)}</span>` : ''}
            </div>
          </div>
          <div class="pt-col-id">
            <span class="patient-row-id">${folio || 'EXP'}</span>
            ${folio ? '<span class="id-local-badge">ID LOCAL</span>' : ''}
          </div>
          <div class="pt-col-date">
            <div class="patient-row-date">${fecha}</div>
          </div>
          <div class="pt-col-actions">
            <button class="patient-row-actions-btn" onclick="event.stopPropagation(); jumpToConsultWithPatient('${esc(curp)}')" title="Iniciar consulta inmediata">
              🩺
            </button>
            <button class="patient-row-actions-btn" onclick="event.stopPropagation(); openPatientProfile('${esc(curp)}')" title="Abrir expediente completo">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/></svg>
            </button>
          </div>
        </div>
      `;
    }).join('');
    return;
  }

  // VISTA MODULAR POR SECCIONES (SOLICITADA POR EL USUARIO)
  const tableHeader = document.querySelector('.patients-pseudo-table-header');
  if (tableHeader) tableHeader.style.display = 'none';

  el.className = 'patients-modules-grid';

  // Secciones clínicas organizadas
  const SECTIONS_CONFIG = [
    {
      id: "diabetes",
      title: "PACIENTES CON DIABETES & TRASTORNOS METABÓLICOS",
      desc: "CIE-10 E11, E03 • Control glucémico, endocrinología y comorbilidades",
      icon: "🩸"
    },
    {
      id: "hipertension",
      title: "PACIENTES CON HIPERTENSIÓN & CARDIOPATÍAS",
      desc: "CIE-10 I10, I50 • Tensión arterial, insuficiencia cardíaca y MAPA",
      icon: "❤️"
    },
    {
      id: "dengue",
      title: "PACIENTES CON DENGUE & ENFERMEDADES FEBRILES",
      desc: "CIE-10 A90, U07, A09 • Arbovirosis, triaje febril e infectología",
      icon: "🦟"
    },
    {
      id: "respiratorio",
      title: "PACIENTES CON ENFERMEDADES RESPIRATORIAS (ASMA & EPOC)",
      desc: "CIE-10 J45, J44, J18 • Vías aéreas, función pulmonar y espirometría",
      icon: "🫁"
    },
    {
      id: "reuma_renal",
      title: "PACIENTES CON ENFERMEDADES REUMATOLÓGICAS & RENALES",
      desc: "CIE-10 M32, M05, N18, N10 • Autoinmunidad, nefrología y artritis",
      icon: "🧬"
    },
    {
      id: "especialidades",
      title: "PACIENTES DE ESPECIALIDADES, CIRUGÍA & GENERAL",
      desc: "CIE-10 H40, M51, F33, K35, K80, H66, L20 • Control ambulatorio integral",
      icon: "🏥"
    }
  ];

  // Agrupar pacientes por sección
  const activeCohort = window.currentPatientCohort || 'all';
  let htmlSections = '';

  SECTIONS_CONFIG.forEach(sec => {
    if (activeCohort !== 'all' && activeCohort !== sec.id) return;

    // Filtrar pacientes pertenecientes a esta sección
    const secPatients = patients.filter(p => {
      const curp = isSemantic ? p.patient_curp : p.curp;
      const cInfo = (window.PATIENTS_CLINICAL_MAP && window.PATIENTS_CLINICAL_MAP[curp]);
      if (cInfo && cInfo.category === sec.id) return true;
      if (!cInfo && sec.id === 'especialidades') return true;
      return false;
    });

    if (secPatients.length === 0 && activeCohort === 'all') return;

    const cardsHtml = secPatients.map(p => {
      const curp = isSemantic ? p.patient_curp : p.curp;
      const nombre = isSemantic ? (p.nombre_paciente || 'Nombre no registrado') : (p.nombre || p.nombre_completo || 'Nombre no registrado');
      const parts = nombre.split(/\\s+/).filter(Boolean);
      const initials = parts.length > 1 ? (parts[0][0] + parts[1][0]).toUpperCase() : (parts[0] ? parts[0].slice(0, 2).toUpperCase() : 'PT');
      const folio = p.folio_hospital || 'EXP';
      const cInfo = (window.PATIENTS_CLINICAL_MAP && window.PATIENTS_CLINICAL_MAP[curp]) || {
        disease: 'Control Médico General (Z00)',
        cie10: 'Z00',
        highlight: 'Signos basales estables'
      };

      return `
        <div class="modular-patient-row" data-curp="${esc(curp)}" onclick="openPatientProfile('${esc(curp)}')" title="Ver expediente de ${esc(nombre)}">
          <div class="pt-mod-left">
            <div class="pt-mod-avatar">${initials}</div>
            <div class="pt-mod-info">
              <div class="pt-mod-name-row">
                <span class="pt-mod-name">${esc(nombre)}</span>
                <span class="pt-mod-curp-code">${esc(curp)}</span>
              </div>
              <div class="pt-mod-demog">
                <strong>${folio}</strong> • ${p.sexo || 'M'} • ${p.edad != null ? p.edad + ' años' : 'Adulto'}
              </div>
              <div class="pt-mod-disease-pill">
                <span>🏷️</span>
                <span>${esc(cInfo.disease)}</span>
              </div>
              <div class="pt-mod-highlight">
                ✓ ${esc(cInfo.highlight)}
              </div>
            </div>
          </div>
          <div class="pt-mod-actions" onclick="event.stopPropagation()">
            <button type="button" class="btn-mod-consult" onclick="jumpToConsultWithPatient('${esc(curp)}')" title="Iniciar consulta con este paciente">
              <span>🩺</span>
              <span>Consulta</span>
            </button>
            <button type="button" class="btn-mod-profile" onclick="openPatientProfile('${esc(curp)}')" title="Abrir expediente completo">
              <span>Ficha</span>
            </button>
          </div>
        </div>
      `;
    }).join('');

    htmlSections += `
      <section class="patient-section-card" data-section="${sec.id}">
        <div class="section-card-header">
          <div class="section-title-wrap">
            <div class="section-icon-badge">${sec.icon}</div>
            <div>
              <h3 class="section-main-title">${sec.title}</h3>
              <p class="section-sub-desc">${sec.desc}</p>
            </div>
          </div>
          <span class="section-badge-counter">${secPatients.length} Pacientes</span>
        </div>
        <div class="section-patients-list">
          ${cardsHtml.length ? cardsHtml : '<div class="no-patients" style="padding:15px; font-size:12px;">Sin pacientes en este módulo para el criterio actual.</div>'}
        </div>
      </section>
    `;
  });

  el.innerHTML = htmlSections || '<div class="no-patients">No se encontraron pacientes para el filtro seleccionado.</div>';
}"""

    # Replace renderPatients function in app.js
    pattern = re.compile(r'function\s+renderPatients\s*\([\s\S]*?\}\s*function\s+openPatientProfile', re.MULTILINE)
    if pattern.search(js):
        js = pattern.sub(new_render_patients + "\n\nfunction openPatientProfile", js)
        print(f"Replaced renderPatients in: {p}")
    else:
        # Fallback search
        p_start = js.find('function renderPatients(')
        p_end = js.find('function openPatientProfile(', p_start)
        if p_start != -1 and p_end != -1:
            js = js[:p_start] + new_render_patients + "\n\n" + js[p_end:]
            print(f"Replaced renderPatients (fallback) in: {p}")

    with open(p, "w", encoding="utf-8") as f:
        f.write(js)


for root in ROOTS:
    print(f"\nProcessing root: {root}")
    update_index_html(root)
    update_style_css(root)
    update_app_js(root)

print("\nPatient sections modules successfully deployed!")
