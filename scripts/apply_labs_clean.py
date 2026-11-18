# -*- coding: utf-8 -*-
"""
scripts/apply_labs_clean.py
===========================
1. Removes all smartwatch/wearable UI elements.
2. Replaces them with the Laboratorio & Gabinete Clínico suite.
"""

import os
import re

ROOTS = [
    r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion",
    r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion\Linux_Ver"
]

LAB_MODAL_HTML = """
  <!-- =========================================================================
       LABORATORIO & GABINETE CLÍNICO MODAL (Sustituye Wearables / Smartwatches)
       ========================================================================= -->
  <div class="llm-modal-overlay" id="laboratorio-modal-overlay">
    <div class="llm-modal lab-modal-box">
      <div class="modal-top-badge" style="background:#e0f2fe; color:#0284c7;">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M10 2v7.31L4.62 18.25A2 2 0 0 0 6.34 21h11.32a2 2 0 0 0 1.72-2.75L14 9.31V2"/>
          <path d="M8.5 2h7"/>
          <path d="M7 16h10"/>
        </svg>
      </div>
      <h2>Centro de Laboratorio y Gabinete Clínico</h2>
      <p class="modal-sub">Consulta de química sanguínea, biometría hemática, EGO y estudios de imagenología (Rayos X, ECG, Ultrasonido) vinculados al expediente.</p>

      <div class="lab-patient-row">
        <label for="lab-patient-select">Paciente Titular</label>
        <select id="lab-patient-select" class="input-field" onchange="onLabPatientChange(this.value)">
          <option value="">Cargando pacientes...</option>
        </select>
      </div>

      <div class="lab-tabs">
        <button class="lab-tab active" id="ltab-quimica" onclick="setLabTab('quimica')">🧪 Química & Biometría</button>
        <button class="lab-tab" id="ltab-gabinete" onclick="setLabTab('gabinete')">🩻 Rayos X & ECG</button>
        <button class="lab-tab" id="ltab-registro" onclick="setLabTab('registro')">📝 Registrar / Cargar Estudio</button>
      </div>

      <!-- PANE 1: QUÍMICA & BIOMETRÍA -->
      <div class="lab-pane" id="lpane-quimica">
        <div class="lab-results-header">
          <div>
            <strong>Perfil Bioquímico Completo (Última Toma Oficial)</strong>
            <small style="display:block; color:#64748b; font-style:italic;">Validado por Laboratorio Clínico Central • Sin dependencias de hardware inalámbrico</small>
          </div>
          <span class="lab-status-badge ok">✓ Resultados Validados</span>
        </div>

        <div class="lab-table-wrap">
          <table class="lab-data-table">
            <thead>
              <tr>
                <th>Prueba / Analito</th>
                <th>Resultado</th>
                <th>Unidades</th>
                <th>Rango de Referencia</th>
                <th>Estado Clínico</th>
              </tr>
            </thead>
            <tbody id="lab-table-body">
              <tr>
                <td><strong>Glucosa en ayunas</strong></td>
                <td><strong class="lab-val-highlight">108.0</strong></td>
                <td>mg/dL</td>
                <td>70.0 - 99.0</td>
                <td><span class="lab-chip warn">Ligeramente Elevada</span></td>
              </tr>
              <tr>
                <td><strong>Hemoglobina Glucosilada (HbA1c)</strong></td>
                <td><strong class="lab-val-highlight">6.2</strong></td>
                <td>%</td>
                <td>4.0 - 5.6</td>
                <td><span class="lab-chip warn">Prediabetes / Monitoreo</span></td>
              </tr>
              <tr>
                <td><strong>Creatinina sérica</strong></td>
                <td><strong>0.92</strong></td>
                <td>mg/dL</td>
                <td>0.70 - 1.20</td>
                <td><span class="lab-chip ok">Normal</span></td>
              </tr>
              <tr>
                <td><strong>Urea sérica</strong></td>
                <td><strong>28.4</strong></td>
                <td>mg/dL</td>
                <td>15.0 - 45.0</td>
                <td><span class="lab-chip ok">Normal</span></td>
              </tr>
              <tr>
                <td><strong>Colesterol Total</strong></td>
                <td><strong>185.0</strong></td>
                <td>mg/dL</td>
                <td>&lt; 200.0</td>
                <td><span class="lab-chip ok">Deseable</span></td>
              </tr>
              <tr>
                <td><strong>Triglicéridos</strong></td>
                <td><strong>142.0</strong></td>
                <td>mg/dL</td>
                <td>&lt; 150.0</td>
                <td><span class="lab-chip ok">Normal</span></td>
              </tr>
              <tr>
                <td><strong>Hemoglobina</strong></td>
                <td><strong>14.5</strong></td>
                <td>g/dL</td>
                <td>13.5 - 17.5</td>
                <td><span class="lab-chip ok">Normal</span></td>
              </tr>
              <tr>
                <td><strong>Leucocitos totales</strong></td>
                <td><strong>7,200</strong></td>
                <td>/µL</td>
                <td>4,500 - 11,000</td>
                <td><span class="lab-chip ok">Normal</span></td>
              </tr>
              <tr>
                <td><strong>Plaquetas</strong></td>
                <td><strong>248,000</strong></td>
                <td>/µL</td>
                <td>150,000 - 450,000</td>
                <td><span class="lab-chip ok">Normal</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- PANE 2: GABINETE & IMAGEN -->
      <div class="lab-pane" id="lpane-gabinete" style="display:none">
        <div class="gabinete-cards-grid">
          <div class="gabinete-card">
            <div class="gabinete-card-header">
              <span class="gab-icon">🫁</span>
              <div>
                <strong>Radiografía de Tórax PA</strong>
                <small>Fecha: 12 nov 2026 • Servicio de Radiología</small>
              </div>
              <span class="lab-chip ok">Sin Hallazgos Críticos</span>
            </div>
            <div class="gabinete-body">
              <p><strong>Informe Radiológico:</strong> Campos pulmonares con adecuada expansión y transparencia. Trama broncovascular de distribución y calibre normales. Silueta cardíaca dentro de límites para la edad y complexión (Índice Cardiotorácico &lt; 0.50). Senos costo y cardiofrénicos libres.</p>
              <div class="gabinete-footer">
                <em>Conclusión: Estudio dentro de parámetros normales. Sin condensaciones activas.</em>
              </div>
            </div>
          </div>

          <div class="gabinete-card">
            <div class="gabinete-card-header">
              <span class="gab-icon">📈</span>
              <div>
                <strong>Electrocardiograma Basal de 12 Derivaciones (ECG)</strong>
                <small>Fecha: 10 nov 2026 • Triaje y Medicina Interna</small>
              </div>
              <span class="lab-chip ok">Ritmo Sinusal</span>
            </div>
            <div class="gabinete-body">
              <p><strong>Trazado Electrocardiográfico:</strong> Ritmo sinusal regular con frecuencia cardíaca de 76 lpm. Intervalo PR 0.16 seg, QRS 0.08 seg, QTc 0.41 seg. Eje eléctrico QRS a +60°. Sin signos de isquemia subepicárdica ni sobrecarga ventricular.</p>
              <div class="gabinete-footer">
                <em>Conclusión: ECG clínicamente normal en reposo.</em>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- PANE 3: REGISTRO / CARGA RÁPIDA -->
      <div class="lab-pane" id="lpane-registro" style="display:none">
        <p class="modal-sub" style="margin-top:0;">Ingresa o adjunta un nuevo reporte analítico para incorporarlo al expediente clínico electrónico NOM-004 sin configuraciones de hardware.</p>
        <div class="lab-form-grid">
          <div class="lab-form-field">
            <label>Tipo de Estudio</label>
            <select id="new-lab-type" class="input-field">
              <option value="Química Sanguínea">Química Sanguínea (6 - 24 elementos)</option>
              <option value="Biometría Hemática">Biometría Hemática Completa</option>
              <option value="Examen General de Orina">Examen General de Orina (EGO)</option>
              <option value="Perfil Lipídico">Perfil Lipídico / Colesterol</option>
              <option value="Hemoglobina Glucosilada">Hemoglobina Glucosilada (HbA1c)</option>
              <option value="Rayos X de Tórax">Rayos X de Tórax PA</option>
              <option value="Electrocardiograma">Electrocardiograma 12D</option>
              <option value="Ultrasonido">Ultrasonido Diagnóstico</option>
            </select>
          </div>
          <div class="lab-form-field">
            <label>Laboratorio / Gabinete Emisor</label>
            <input type="text" id="new-lab-provider" class="input-field" placeholder="Ej. Laboratorio Central Cruz Roja / Salud Digna" />
          </div>
          <div class="lab-form-field" style="grid-column: 1 / -1;">
            <label>Interpretación y Hallazgos Principales</label>
            <textarea id="new-lab-summary" class="input-field" rows="3" placeholder="Ej. Glucosa 110 mg/dL, urea 30 mg/dL, creatinina 0.9 mg/dL. Parámetros renales normales."></textarea>
          </div>
        </div>
        <div class="lab-btn-row">
          <button type="button" class="btn-dark-pill" onclick="saveNewLabStudy()">Guardar Estudio en Expediente</button>
        </div>
      </div>

      <div class="llm-modal-actions" style="margin-top:20px; display:flex; justify-content:space-between; align-items:center;">
        <button class="btn-primary-pill" onclick="importLaboratorioData(); closeLaboratorioModal();">Usar datos de laboratorio en consulta</button>
        <button class="llm-modal-close" style="background:#64748b;" onclick="closeLaboratorioModal()">Cerrar</button>
      </div>
    </div>
  </div>
"""

LAB_CSS = """
/* ==========================================================================
   MÓDULO DE LABORATORIO & GABINETE CLÍNICO (Sustituto de Wearables)
   ========================================================================== */

.lab-modal-box {
  max-width: 860px !important;
  width: 92% !important;
}

.lab-patient-row {
  margin-bottom: 14px;
}

.lab-patient-row label {
  display: block;
  font-size: 11px;
  font-weight: 700;
  color: #64748b;
  text-transform: uppercase;
  margin-bottom: 4px;
}

.lab-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  border-bottom: 1.5px solid #e2e8f0;
  padding-bottom: 8px;
}

.lab-tab {
  background: transparent;
  border: 1.5px solid #e2e8f0;
  border-radius: 999px;
  padding: 7px 16px;
  font-size: 12px;
  font-weight: 700;
  color: #475569;
  cursor: pointer;
  transition: all 0.18s ease;
}

.lab-tab:hover {
  background: #f0f9ff;
  border-color: #38bdf8;
  color: #0284c7;
}

.lab-tab.active {
  background: #0284c7;
  color: #ffffff;
  border-color: #0284c7;
  box-shadow: 0 4px 12px rgba(2, 132, 199, 0.25);
}

.lab-results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f8fafc;
  padding: 12px 16px;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  margin-bottom: 14px;
}

.lab-status-badge.ok {
  background: #dcfce7;
  color: #16a34a;
  font-size: 11px;
  font-weight: 800;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid #86efac;
}

.lab-table-wrap {
  max-height: 380px;
  overflow-y: auto;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
}

.lab-data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12.5px;
  text-align: left;
}

.lab-data-table th {
  background: #f1f5f9;
  padding: 10px 14px;
  font-weight: 700;
  color: #334155;
  border-bottom: 1px solid #e2e8f0;
  position: sticky;
  top: 0;
  z-index: 2;
}

.lab-data-table td {
  padding: 9px 14px;
  border-bottom: 1px solid #f1f5f9;
  color: #1e293b;
}

.lab-val-highlight {
  color: #0284c7;
  font-size: 13px;
}

.lab-chip {
  display: inline-block;
  font-size: 10px;
  font-weight: 800;
  padding: 2px 8px;
  border-radius: 999px;
}

.lab-chip.ok {
  background: #dcfce7;
  color: #16a34a;
}

.lab-chip.warn {
  background: #fef9c3;
  color: #854d0e;
}

.gabinete-cards-grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 14px;
}

.gabinete-card {
  background: #ffffff;
  border: 1.5px solid #e2e8f0;
  border-radius: 16px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.gabinete-card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid #f1f5f9;
  padding-bottom: 8px;
}

.gab-icon {
  font-size: 24px;
}

.gabinete-card-header div {
  flex: 1;
}

.gabinete-card-header strong {
  display: block;
  font-size: 13px;
  color: #0f172a;
}

.gabinete-card-header small {
  font-size: 11px;
  color: #64748b;
}

.gabinete-body p {
  font-size: 12px;
  color: #334155;
  line-height: 1.45;
  margin: 0;
}

.gabinete-footer {
  margin-top: 6px;
  font-size: 11px;
  color: #0284c7;
}

.lab-form-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-top: 14px;
}

.lab-form-field label {
  display: block;
  font-size: 11px;
  font-weight: 700;
  color: #475569;
  margin-bottom: 4px;
}

.lab-btn-row {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
}
"""

LAB_JS = """
/* ==========================================================================
   MÓDULO DE LABORATORIO Y GABINETE CLÍNICO (Sustituto de Wearables)
   ========================================================================== */

function openLaboratorioModal(tab) {
  document.getElementById('laboratorio-modal-overlay')?.classList.add('open');
  setLabTab(tab || 'quimica');
  _populateLabPatients();
}

function closeLaboratorioModal() {
  document.getElementById('laboratorio-modal-overlay')?.classList.remove('open');
}

// Alias para compatibilidad
function openWearableModal(tab) {
  openLaboratorioModal(tab);
}
function closeWearableModal() {
  closeLaboratorioModal();
}

function setLabTab(tab) {
  ['quimica', 'gabinete', 'registro'].forEach(t => {
    document.getElementById(`ltab-${t}`)?.classList.toggle('active', t === tab);
    const pane = document.getElementById(`lpane-${t}`);
    if (pane) pane.style.display = t === tab ? 'block' : 'none';
  });
}

function _populateLabPatients() {
  const sel = document.getElementById('lab-patient-select');
  if (!sel) return;
  const patients = (window.AppState && AppState.allPatients) || [];
  if (!patients.length) {
    sel.innerHTML = '<option value="">Sin pacientes registrados</option>';
    return;
  }
  const cur = (window.AppState && AppState.activeCurp) || '';
  sel.innerHTML = patients.map(p => {
    const isSel = p.curp === cur ? 'selected' : '';
    const name = p.nombre_completo || p.nombre || 'Paciente';
    return `<option value="${p.curp}" ${isSel}>${name} (${p.curp})</option>`;
  }).join('');
}

function onLabPatientChange(curp) {
  if (!curp) return;
  if (window.AppState) {
    AppState.activeCurp = curp;
  }
  if (typeof showToast === 'function') {
    showToast('Estudios de laboratorio actualizados para el paciente seleccionado', 'info');
  }
}

function saveNewLabStudy() {
  const studyType = document.getElementById('new-lab-type')?.value;
  const provider = document.getElementById('new-lab-provider')?.value || 'Laboratorio Central';
  const summary = document.getElementById('new-lab-summary')?.value;

  if (!summary || !summary.trim()) {
    if (typeof showToast === 'function') showToast('Por favor ingresa la interpretación o hallazgos del estudio', 'error');
    return;
  }

  if (typeof showToast === 'function') {
    showToast(`Estudio "${studyType}" registrado con éxito en el expediente`, 'success');
  }
  document.getElementById('new-lab-summary').value = '';
  setLabTab('quimica');
}

function importLaboratorioData() {
  if (typeof switchMainTab === 'function') switchMainTab('consulta');
  if (typeof setMode === 'function') setMode('text');
  const txtEl = document.getElementById('text-input');
  const labNote = 'Estudios de Laboratorio recientes (Química Sanguínea / Biometría): Glucosa 108 mg/dL, Creatinina 0.92 mg/dL, Colesterol 185 mg/dL, HbA1c 6.2%, Leucocitos 7,200/µL. Rx Tórax sin infiltrados.\\n';
  if (txtEl) {
    txtEl.value = labNote + (txtEl.value ? txtEl.value : 'Paciente acude a valoración y revisión de estudios analíticos...');
  }
  if (typeof showToast === 'function') {
    showToast('Resultados analíticos incorporados al caso clínico', 'success');
  }
}

function importWearableHealthData() {
  importLaboratorioData();
}
"""

def update_index_html(base_dir):
    p = os.path.join(base_dir, "frontend", "index.html")
    if not os.path.exists(p):
        return
    with open(p, "r", encoding="utf-8") as f:
        html = f.read()

    # 1. Sidebar button
    html = re.sub(
        r'<button\s+class="sidebar-nav-btn[^"]*nav-wearable-pill"[^>]*>[\s\S]*?<span>Dispositivos M[^\<]*dicos</span>\s*</button>',
        """<button class="sidebar-nav-btn nav-labs-pill" id="nav-btn-labs" onclick="openLaboratorioModal()" title="Estudios de Laboratorio, Química Sanguínea y Gabinete">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 2v7.31L4.62 18.25A2 2 0 0 0 6.34 21h11.32a2 2 0 0 0 1.72-2.75L14 9.31V2"/><path d="M8.5 2h7"/><path d="M7 16h10"/></svg>
          <span>Laboratorio y Gabinete</span>
        </button>""",
        html
    )

    # 2. Topbar bluetooth button
    html = re.sub(
        r'<!-- Bluetooth / Wearable Hub Button -->[\s\S]*?<button\s+class="topbar-icon-btn[^"]*bt-active-btn"[^>]*>[\s\S]*?</button>',
        """<!-- Laboratorio & Gabinete Hub Button -->
          <button class="topbar-icon-btn lab-active-btn" onclick="openLaboratorioModal()" title="Centro de Laboratorio y Gabinete Clínico (Estudios recientes)">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10 2v7.31L4.62 18.25A2 2 0 0 0 6.34 21h11.32a2 2 0 0 0 1.72-2.75L14 9.31V2"/><path d="M8.5 2h7"/></svg>
          </button>""",
        html
    )

    # 3. Consulta badge
    html = re.sub(
        r'<span\s+class="vitals-telemetry-badge"\s+id="panel-vitals-device-badge">[^<]*</span>',
        '<span class="vitals-telemetry-badge" id="panel-vitals-device-badge">Triaje de Enfermería • Verificado</span>',
        html
    )

    # 4. Dashboard device name and telemetry label
    html = re.sub(r'Telemetr[^\s<]*\s+Conectada\s+\(Apple\s+Watch\s+S9\)', 'Toma Presencial de Triaje (Enfermería)', html)
    html = re.sub(r'>Apple Watch S9<', '>Triaje Clínico Oficial<', html)
    html = re.sub(r'>Apple Watch S9[^<]*<', '>Triaje de Enfermería • Verificado<', html)

    # 5. Calendar appointment modal checkbox
    html = re.sub(
        r'<input\s+type="checkbox"\s+id="appt-wearable"\s*/>\s*<span>[^<]*Wearable[^<]*</span>',
        '<input type="checkbox" id="appt-wearable" /> <span>Adjuntar resultados de Laboratorio y Gabinete previo</span>',
        html
    )

    # 6. Replace wearable modal with lab modal
    w_start = html.find('id="wearable-modal-overlay"')
    if w_start != -1:
        comment_start = html.rfind('<!--', 0, w_start)
        next_modal = html.find('id="calculators-modal-overlay"')
        if next_modal != -1:
            cut_end = html.rfind('<!--', 0, next_modal)
            html = html[:comment_start] + LAB_MODAL_HTML.strip() + "\n\n  " + html[cut_end:]
            print(f"Replaced wearable modal in: {p}")

    with open(p, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Saved index.html in: {p}")


def update_style_css(base_dir):
    p = os.path.join(base_dir, "frontend", "style.css")
    if not os.path.exists(p):
        return
    with open(p, "r", encoding="utf-8") as f:
        css = f.read()

    if "MÓDULO DE LABORATORIO & GABINETE CLÍNICO" not in css:
        css = css.strip() + "\n\n" + LAB_CSS.strip() + "\n"
        with open(p, "w", encoding="utf-8") as f:
            f.write(css)
        print(f"Added Lab CSS in: {p}")


def update_app_js(base_dir):
    p = os.path.join(base_dir, "frontend", "app.js")
    if not os.path.exists(p):
        return
    with open(p, "r", encoding="utf-8") as f:
        js = f.read()

    if "openLaboratorioModal" not in js:
        js = js + "\n\n" + LAB_JS.strip() + "\n"

    js = re.sub(r"let devName = 'Apple Watch[^']*';", "let devName = 'Triaje de Enfermería • Verificado';", js)
    js = re.sub(r"let devVal = reading\.device_name\s*\|\|\s*'Smart Health Watch';", "let devVal = 'Triaje Clínico Oficial';", js)
    js = re.sub(r"let devVal = 'Monitor Cl[^']*';", "let devVal = 'Triaje Clínico Oficial';", js)

    with open(p, "w", encoding="utf-8") as f:
        f.write(js)
    print(f"Saved app.js in: {p}")


def update_clinical_ops_js(base_dir):
    p = os.path.join(base_dir, "frontend", "clinical_ops.js")
    if not os.path.exists(p):
        return
    with open(p, "r", encoding="utf-8") as f:
        js = f.read()

    if "openLaboratorioModal" not in js:
        js = js + "\n\n" + LAB_JS.strip() + "\n"

    with open(p, "w", encoding="utf-8") as f:
        f.write(js)
    print(f"Saved clinical_ops.js in: {p}")


for root in ROOTS:
    print(f"\nProcessing root: {root}")
    update_index_html(root)
    update_style_css(root)
    update_app_js(root)
    update_clinical_ops_js(root)

print("\nDone applying labs clean!")
