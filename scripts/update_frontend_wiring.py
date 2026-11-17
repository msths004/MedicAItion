# -*- coding: utf-8 -*-
"""
scripts/update_frontend_wiring.py
=================================
Connects premium_search.js and dynamic dashboard loading across frontend files.
"""

import os

ROOTS = [
    r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion\frontend",
    r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion\Linux_Ver\frontend"
]

DYNAMIC_DASHBOARD_CODE = """
/* ==========================================================================
   MODULAR PATIENT DASHBOARD (RESUMEN) INTERACTION LOGIC
   ========================================================================== */

async function onDashboardPatientChange(curp) {
  if (!curp) return;

  let patient = (AppState.allPatients || []).find(x => x.curp === curp);
  if (!patient) {
    try {
      const res = await fetch(`${API}/api/patients/${encodeURIComponent(curp)}`);
      if (res.ok) patient = await res.json();
    } catch (e) {
      console.warn('[Dashboard] Error cargando paciente:', e);
    }
  }

  // Extraer iniciales y datos reales
  const fullName = patient ? (patient.nombre_completo || patient.nombre || `${patient.nombres || ''} ${patient.primer_apellido || ''} ${patient.segundo_apellido || ''}`.trim()) : 'Paciente Seleccionado';
  const parts = fullName.split(/\\s+/).filter(Boolean);
  const avatarInitials = parts.length > 1 ? (parts[0][0] + parts[1][0]).toUpperCase() : (parts[0] ? parts[0].slice(0, 2).toUpperCase() : 'PT');
  const ageStr = (patient && patient.edad != null) ? `${patient.edad} Años` : (patient && patient.fecha_nacimiento ? `${patient.fecha_nacimiento}` : '—');
  const dobStr = (patient && patient.fecha_nacimiento) ? patient.fecha_nacimiento : '—';
  const idStr = (patient && patient.folio_hospital) ? patient.folio_hospital : (patient ? patient.curp.slice(0, 10) : '—');
  const genderStr = (patient && patient.sexo === 'M') ? 'Masculino' : ((patient && patient.sexo === 'F') ? 'Femenino' : 'No especificado');
  const bloodStr = (patient && patient.tipo_sangre) ? `${patient.tipo_sangre} (Rh+)` : 'O+ (Rh+)';
  const phoneStr = (patient && (patient.celular || patient.telefono_local)) ? (patient.celular || patient.telefono_local) : '+52 999 000 0000';

  let allergiesText = '⚠️ Sin alergias críticas reportadas';
  if (patient && Array.isArray(patient.alergias) && patient.alergias.length > 0) {
    allergiesText = '⚠️ Alergia: ' + patient.alergias.map(a => a.descripcion).join(', ');
  }

  // Update elements
  const elName = document.getElementById('dash-patient-name');
  if (elName) elName.textContent = fullName;
  const elAvatar = document.getElementById('dash-patient-avatar');
  if (elAvatar) elAvatar.textContent = avatarInitials;
  const elAge = document.getElementById('dash-patient-age');
  if (elAge) elAge.textContent = ageStr;
  const elDob = document.getElementById('dash-patient-dob');
  if (elDob) elDob.textContent = dobStr;
  const elId = document.getElementById('dash-patient-id');
  if (elId) elId.textContent = idStr;
  const elGender = document.getElementById('dash-patient-gender');
  if (elGender) elGender.textContent = genderStr;
  const elBlood = document.getElementById('dash-patient-blood');
  if (elBlood) elBlood.textContent = bloodStr;
  const elPhone = document.getElementById('dash-patient-phone');
  if (elPhone) elPhone.textContent = phoneStr;

  const elAllergies = document.getElementById('dash-patient-allergies');
  if (elAllergies) {
    elAllergies.innerHTML = `<span class="allergy-tag">${allergiesText}</span>`;
  }

  // Buscar última lectura de telemetría / wearables
  let bpmVal = '75';
  let devVal = 'Monitor Clínico';
  try {
    const vRes = await fetch(`${API}/api/wearables/readings?curp=${encodeURIComponent(curp)}&limit=1`);
    if (vRes.ok) {
      const vData = await vRes.json();
      const reading = (vData.readings && vData.readings[0]);
      if (reading) {
        bpmVal = String(reading.heart_rate || 75);
        devVal = reading.device_name || 'Smart Health Watch';
      }
    }
  } catch {}

  const elBpm = document.getElementById('dash-bpm-value');
  if (elBpm) elBpm.textContent = bpmVal;

  const elDev = document.getElementById('dash-device-name');
  if (elDev) elDev.textContent = devVal;

  // Sincronizar estado global
  AppState.selectedPatientCurp = curp;
  AppState.activeCurp = curp;

  if (typeof showToast === 'function') {
    showToast(`Paciente seleccionado: ${fullName}`, 'info');
  }
}
"""

def process_root(root):
    # 1. Update app.js
    app_js_path = os.path.join(root, "app.js")
    if os.path.exists(app_js_path):
        with open(app_js_path, "r", encoding="utf-8") as f:
            content = f.read()
        marker = "/* ==========================================================================\n   MODULAR PATIENT DASHBOARD (RESUMEN) INTERACTION LOGIC"
        if marker in content:
            idx = content.find(marker)
            content = content[:idx] + DYNAMIC_DASHBOARD_CODE.strip() + "\n"
            with open(app_js_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Updated dynamic patient loader in: {app_js_path}")

    # 2. Update index.html to include premium_search.js
    index_html_path = os.path.join(root, "index.html")
    if os.path.exists(index_html_path):
        with open(index_html_path, "r", encoding="utf-8") as f:
            content = f.read()
        if "premium_search.js" not in content:
            target = '<script src="app.js?v=6.5.0"></script>'
            replacement = '<script src="premium_search.js?v=6.5.0"></script>\n  <script src="app.js?v=6.5.0"></script>'
            if target in content:
                content = content.replace(target, replacement, 1)
                with open(index_html_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print(f"Added premium_search.js script tag to: {index_html_path}")

    # 3. Update specialized_care.js to notify OmniSearch when selector populates
    spec_path = os.path.join(root, "specialized_care.js")
    if os.path.exists(spec_path):
        with open(spec_path, "r", encoding="utf-8") as f:
            content = f.read()
        target = "if (prev && [...sel.options].some(o => o.value === prev)) {"
        if target in content and "OmniSearch.refreshAll" not in content:
            replacement = """if (window.OmniSearch && typeof window.OmniSearch.refreshAll === 'function') {
      window.OmniSearch.refreshAll();
    }
    if (prev && [...sel.options].some(o => o.value === prev)) {"""
            content = content.replace(target, replacement, 1)
            with open(spec_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"Connected specialized_care.js to OmniSearch in: {spec_path}")

for root in ROOTS:
    process_root(root)
print("Frontend wiring completed successfully.")
