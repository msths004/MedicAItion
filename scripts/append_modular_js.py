# -*- coding: utf-8 -*-
import os

BASE_DIR = r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion"
APP_PATH = os.path.join(BASE_DIR, "frontend", "app.js")
LINUX_APP_PATH = os.path.join(BASE_DIR, "Linux_Ver", "frontend", "app.js")

with open(APP_PATH, "r", encoding="utf-8") as f:
    js = f.read()

modular_js = """
/* ==========================================================================
   MODULAR PATIENT DASHBOARD (RESUMEN) INTERACTION LOGIC
   ========================================================================== */

function onDashboardPatientChange(curp) {
  const mockData = {
    'MOBK070228HYNRTVA3': {
      name: 'Kevin Enrique Morales Bautista',
      avatar: 'KM',
      age: '19 Años',
      dob: '28/02/2007',
      id: 'PT-2026-0001',
      gender: 'Masculino',
      blood: 'A+ (Rh+)',
      phone: '+52 999 415 6931',
      allergies: '⚠️ Alergia Crítica: Penicilina, AINEs (Ketorolaco)',
      bpm: '82',
      device: 'Apple Watch S9'
    },
    'GOPC790814HYNCLN04': {
      name: 'Carlos Manuel González Pech',
      avatar: 'CG',
      age: '47 Años',
      dob: '14/08/1979',
      id: 'PT-2026-0842',
      gender: 'Masculino',
      blood: 'O+ (Rh+)',
      phone: '+52 999 234 5678',
      allergies: '⚠️ Sin alergias medicamentosas conocidas',
      bpm: '74',
      device: 'Garmin Active'
    },
    'TESTCURP1234567890': {
      name: 'Juan Pérez Gómez',
      avatar: 'JP',
      age: '45 Años',
      dob: '10/05/1981',
      id: 'PT-2026-0319',
      gender: 'Masculino',
      blood: 'B+ (Rh+)',
      phone: '+52 999 876 5432',
      allergies: '⚠️ Alergia a Sulfamidas y Trimetoprima',
      bpm: '78',
      device: 'Galaxy Watch 6'
    }
  };

  const p = mockData[curp] || mockData['MOBK070228HYNRTVA3'];

  // Update elements
  const elName = document.getElementById('dash-patient-name');
  if (elName) elName.textContent = p.name;
  const elAvatar = document.getElementById('dash-patient-avatar');
  if (elAvatar) elAvatar.textContent = p.avatar;
  const elAge = document.getElementById('dash-patient-age');
  if (elAge) elAge.textContent = p.age;
  const elDob = document.getElementById('dash-patient-dob');
  if (elDob) elDob.textContent = p.dob;
  const elId = document.getElementById('dash-patient-id');
  if (elId) elId.textContent = p.id;
  const elGender = document.getElementById('dash-patient-gender');
  if (elGender) elGender.textContent = p.gender;
  const elBlood = document.getElementById('dash-patient-blood');
  if (elBlood) elBlood.textContent = p.blood;
  const elPhone = document.getElementById('dash-patient-phone');
  if (elPhone) elPhone.textContent = p.phone;

  const elAllergies = document.getElementById('dash-patient-allergies');
  if (elAllergies) {
    elAllergies.innerHTML = `<span class="allergy-tag">${p.allergies}</span>`;
  }

  const elBpm = document.getElementById('dash-bpm-value');
  if (elBpm) elBpm.textContent = p.bpm;

  const elDev = document.getElementById('dash-device-name');
  if (elDev) elDev.textContent = p.device;

  // Also sync consultation context
  if (typeof loadConsultaPatientContext === 'function') {
    loadConsultaPatientContext(curp);
  }

  if (typeof showToast === 'function') {
    showToast(`Paciente seleccionado: ${p.name}`, 'info');
  }
}
"""

if "MODULAR PATIENT DASHBOARD (RESUMEN) INTERACTION LOGIC" not in js:
    with open(APP_PATH, "a", encoding="utf-8") as f:
        f.write("\n" + modular_js)
    with open(LINUX_APP_PATH, "a", encoding="utf-8") as f:
        f.write("\n" + modular_js)
    print("Appended modular JS to app.js and Linux_Ver.")
else:
    print("app.js already contains modular JS.")
