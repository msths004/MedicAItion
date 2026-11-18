"""
update_app_js_interhospital.py — Inyección de lógica interactiva para Red Hospitalaria
"""

import os

JS_PATH = os.path.abspath("frontend/app.js")
LINUX_JS = os.path.abspath("Linux_Ver/frontend/app.js")

JS_LOGIC = """
// =========================================================================
// RED HOSPITALARIA & INTERCONSULTA FEDERADA (NOM-024 / HL7 FHIR R4)
// =========================================================================

let currentNetworkSearchMode = 'urgencias_rojo'; // 'urgencias_rojo' | 'interconsulta_consentida'
let cachedInstitutions = [];

async function initRedHospitalariaView() {
  console.log('[Red Hospitalaria] Inicializando vista de interoperabilidad...');
  try {
    // 1. Obtener estado de la red
    const rStat = await fetch('/api/institutions/status');
    if (rStat.ok) {
      const stat = await rStat.json();
      const nodeEl = document.getElementById('kpi-net-nodes');
      const latEl = document.getElementById('kpi-net-latency');
      const secEl = document.getElementById('kpi-net-security');
      const refEl = document.getElementById('kpi-net-referrals');

      if (nodeEl) nodeEl.textContent = `${stat.nodos_activos} Nodos`;
      if (latEl) latEl.textContent = `${stat.latencia_promedio_ms} ms`;
      if (secEl) secEl.textContent = 'Zero-Knowledge';
      if (refEl) refEl.textContent = `${stat.referencias_activas} Activas`;
    }

    // 2. Cargar instituciones
    const rInst = await fetch('/api/institutions/');
    if (rInst.ok) {
      cachedInstitutions = await rInst.json();
      renderHospitalNodesGrid(cachedInstitutions);
      populateHospitalSelect(cachedInstitutions);
    }

    // 3. Cargar referencias
    await loadReferralsTable();

    // 4. Cargar bitácora de auditorías
    await loadAuditsTable();

  } catch (err) {
    console.error('[Red Hospitalaria] Error al sincronizar:', err);
    if (typeof showToast === 'function') {
      showToast('Error al conectar con la Red Interhospitalaria', 'error');
    }
  }
}

function renderHospitalNodesGrid(nodes) {
  const container = document.getElementById('hospital-nodes-list');
  if (!container) return;

  if (!nodes || nodes.length === 0) {
    container.innerHTML = '<div style="padding:16px; color:#64748b; font-size:13px;">No hay nodos hospitalarios activos.</div>';
    return;
  }

  container.innerHTML = nodes.map(n => {
    const isLocal = n.clues === 'YUC-CR-001';
    return `
      <div class="hosp-node-card ${isLocal ? 'is-local-base' : ''}">
        <div class="hosp-node-top">
          <div class="hosp-node-title-box">
            <span class="hosp-node-emoji">${isLocal ? '🚑' : '🏥'}</span>
            <div>
              <div class="hosp-node-name">${escapeHtml(n.nombre)}</div>
              <div class="hosp-node-clues">CLUES: <strong>${escapeHtml(n.clues)}</strong> • ${escapeHtml(n.ubicacion || 'Yucatán')}</div>
            </div>
          </div>
          <span class="hosp-status-pill ${isLocal ? 'is-local' : 'is-online'}">
            <span class="pulse-dot"></span>
            ${isLocal ? 'Sede Local' : 'En Línea'}
          </span>
        </div>
        <div class="hosp-node-meta">
          <span class="meta-tag">🏷️ ${escapeHtml(n.nivel || 'Segundo Nivel')}</span>
          <span class="meta-tag">⚡ ${n.latencia_ms || 12} ms</span>
          <span class="meta-tag">🔒 TLS 1.3</span>
        </div>
      </div>
    `;
  }).join('');
}

function populateHospitalSelect(nodes) {
  const sel = document.getElementById('ref-hospital-destino');
  if (!sel) return;
  // Excluir la sede local actual
  const options = nodes.filter(n => n.clues !== 'YUC-CR-001').map(n => {
    return `<option value="${escapeHtml(n.clues)}|${escapeHtml(n.nombre)}">${escapeHtml(n.nombre)} (${escapeHtml(n.nivel || '')})</option>`;
  }).join('');
  if (options) sel.innerHTML = options;
}

async function loadReferralsTable() {
  const tbody = document.getElementById('referrals-tbody');
  if (!tbody) return;

  try {
    const res = await fetch('/api/institutions/referrals');
    if (!res.ok) return;
    const refs = await res.json();

    if (!refs || refs.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:20px; color:#64748b;">No hay órdenes de referencia registradas.</td></tr>';
      return;
    }

    tbody.innerHTML = refs.map(r => {
      let stateClass = 'state-pending';
      let stateLabel = r.estado;
      if (r.estado === 'En_Transito') {
        stateClass = 'state-transit';
        stateLabel = '🚑 En Tránsito';
      } else if (r.estado === 'Aceptada') {
        stateClass = 'state-accepted';
        stateLabel = '✓ Aceptada';
      } else if (r.estado === 'Completada') {
        stateClass = 'state-completed';
        stateLabel = '✓ Completada';
      }

      let prioClass = 'prio-normal';
      if (r.prioridad === 'Urgencia') prioClass = 'prio-urgent';
      else if (r.prioridad === 'Prioritaria') prioClass = 'prio-high';

      return `
        <tr>
          <td><strong style="color:#0284c7;">${escapeHtml(r.id)}</strong><br/><span style="font-size:11px; color:#94a3b8;">${escapeHtml(r.fecha || '')}</span></td>
          <td><strong>${escapeHtml(r.patient_nombre)}</strong><br/><span style="font-size:11.5px; color:#64748b; font-family:monospace;">${escapeHtml(r.patient_curp)}</span></td>
          <td>
            <div style="font-size:12px;"><strong>De:</strong> ${escapeHtml(r.hospital_origen_nombre)}</div>
            <div style="font-size:12px; color:#0284c7;"><strong>A:</strong> ${escapeHtml(r.hospital_destino_nombre)}</div>
          </td>
          <td>
            <div style="font-size:12.5px; font-weight:600;">${escapeHtml(r.diagnostico_cie10)}</div>
            <div style="font-size:11.5px; color:#64748b; max-width:240px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(r.motivo_envio)}">${escapeHtml(r.motivo_envio)}</div>
          </td>
          <td><span class="ref-prio-badge ${prioClass}">${escapeHtml(r.prioridad)}</span></td>
          <td><span class="ref-state-badge ${stateClass}">${stateLabel}</span></td>
          <td>
            <select class="ref-action-select" onchange="updateReferralState('${r.id}', this.value)">
              <option value="" disabled selected>Cambiar estado...</option>
              <option value="Aceptada">Marcar Aceptada</option>
              <option value="En_Transito">Marcar En Tránsito</option>
              <option value="Completada">Marcar Completada</option>
            </select>
          </td>
        </tr>
      `;
    }).join('');
  } catch (e) {
    console.error('[Red Hospitalaria] Error al cargar referencias:', e);
  }
}

async function loadAuditsTable() {
  const tbody = document.getElementById('audits-tbody');
  if (!tbody) return;

  try {
    const res = await fetch('/api/institutions/audits?limit=25');
    if (!res.ok) return;
    const audits = await res.json();

    if (!audits || audits.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:20px; color:#64748b;">Sin eventos de auditoría interhospitalaria registrados.</td></tr>';
      return;
    }

    tbody.innerHTML = audits.map(a => {
      const isRed = a.tipo_acceso === 'URGENCIAS_ROJO';
      return `
        <tr>
          <td style="font-size:12px; white-space:nowrap;">${escapeHtml(a.timestamp)}</td>
          <td><strong>${escapeHtml(a.doctor_nombre)}</strong><br/><span style="font-size:11px; color:#0284c7;">${escapeHtml(a.doctor_cedula)}</span></td>
          <td style="font-size:12px;">${escapeHtml(a.hospital_solicitante)}</td>
          <td><span style="font-family:monospace; font-size:12px; font-weight:700;">${escapeHtml(a.patient_curp)}</span></td>
          <td><span class="ref-prio-badge ${isRed ? 'prio-urgent' : 'prio-normal'}">${isRed ? '🚨 CÓDIGO ROJO' : '📋 CONSULTA'}</span></td>
          <td style="font-size:12px; color:#475569; max-width:220px;" title="${escapeHtml(a.justificacion)}">${escapeHtml(a.justificacion)}</td>
          <td><span class="audit-badge-hmac" title="${escapeHtml(a.firma_digital_hmac)}">✓ HMAC-SHA256</span></td>
        </tr>
      `;
    }).join('');
  } catch (e) {
    console.error('[Red Hospitalaria] Error al cargar auditorías:', e);
  }
}

function setNetworkSearchMode(mode) {
  currentNetworkSearchMode = mode;
  const btnUrg = document.getElementById('btn-mode-urgencias');
  const btnInt = document.getElementById('btn-mode-interconsulta');
  const shTitle = document.getElementById('sh-title');
  const shDesc = document.getElementById('sh-desc');
  const banner = document.getElementById('search-mode-banner');

  if (btnUrg) btnUrg.classList.toggle('active', mode === 'urgencias_rojo');
  if (btnInt) btnInt.classList.toggle('active', mode === 'interconsulta_consentida');

  if (mode === 'urgencias_rojo') {
    if (banner) banner.className = 'safe-harbor-info-banner mode-urgencias';
    if (shTitle) shTitle.textContent = 'MODO URGENCIAS / CÓDIGO ROJO SELECCIONADO (Safe Harbor NOM-024)';
    if (shDesc) shDesc.textContent = 'Acceso instantáneo (<1s) al Núcleo de Salvaguarda Vital: Tipo de sangre, Alergias mortales y Medicamentos de riesgo. Las notas íntimas y consultas de salud mental están estrictamente bloqueadas. Se estampará un sello de auditoría HMAC con su Cédula Profesional (CED-9482710).';
  } else {
    if (banner) banner.className = 'safe-harbor-info-banner mode-interconsulta';
    if (shTitle) shTitle.textContent = 'MODO INTERCONSULTA FORMAL SELECCIONADO (NOM-004 & HL7 FHIR R4)';
    if (shDesc) shDesc.textContent = 'Acceso completo al expediente clínico interoperable previo consentimiento del paciente o firma digital de derivación. Permite exportar Bundle FHIR R4 y antecedentes patológicos consolidados.';
  }

  // Si ya hay una búsqueda activa, refrescarla con el nuevo modo
  const input = document.getElementById('network-search-input');
  if (input && input.value.trim().length >= 3) {
    executeNetworkSearch();
  }
}

function quickFillNetworkSearch(query) {
  const input = document.getElementById('network-search-input');
  if (input) {
    input.value = query;
    executeNetworkSearch();
  }
}

async function executeNetworkSearch() {
  const input = document.getElementById('network-search-input');
  const area = document.getElementById('network-search-results-area');
  if (!input || !area) return;

  const query = input.value.trim();
  if (!query) {
    if (typeof showToast === 'function') showToast('Ingresa un nombre o CURP para buscar en la red', 'info');
    return;
  }

  area.style.display = 'block';
  area.innerHTML = '<div style="padding:24px; text-align:center; color:#0284c7;"><span class="pulse-dot"></span> Consultando 7 nodos hospitalarios federados...</div>';

  try {
    const res = await fetch('/api/institutions/network-search', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        query: query,
        access_mode: currentNetworkSearchMode,
        doctor_nombre: 'Dr. Roberto Morales',
        doctor_cedula: 'CED-9482710',
        clues_solicitante: 'YUC-CR-001',
        hospital_solicitante: 'Cruz Roja Mexicana Delegación Mérida',
        justificacion: currentNetworkSearchMode === 'urgencias_rojo'
          ? 'Triage de emergencias médicas / Código rojo de estabilización'
          : 'Consulta médica programada / Derivación especializada'
      })
    });

    if (!res.ok) {
      area.innerHTML = '<div style="padding:16px; color:#dc2626; background:#fee2e2; border-radius:8px;">Error al comunicar con la red hospitalaria.</div>';
      return;
    }

    const data = await res.json();
    if (!data.encontrado || !data.paciente) {
      area.innerHTML = `
        <div class="network-not-found-card">
          <div style="font-size:28px; margin-bottom:8px;">🔍</div>
          <h4 style="margin:0 0 4px 0; color:#0f172a;">Paciente no localizado en la Red Federada</h4>
          <p style="margin:0; font-size:13px; color:#64748b;">${escapeHtml(data.mensaje || 'No se encontraron expedientes coincidentes con los criterios de búsqueda.')}</p>
        </div>
      `;
      return;
    }

    renderNetworkSearchResult(data);
    // Recargar tabla de auditorías para mostrar el nuevo acceso
    loadAuditsTable();

  } catch (err) {
    console.error('[Red Hospitalaria] Error en búsqueda:', err);
    area.innerHTML = '<div style="padding:16px; color:#dc2626; background:#fee2e2; border-radius:8px;">Fallo de conexión con el directorio federado.</div>';
  }
}

function renderNetworkSearchResult(data) {
  const area = document.getElementById('network-search-results-area');
  if (!area) return;

  const p = data.paciente;
  const isUrg = data.access_mode === 'urgencias_rojo';
  const priv = data.privacidad_garantizada || {};
  const hospList = data.red_hospitalaria?.hospitales || [];

  const alergiasHtml = (p.alergias_criticas && p.alergias_criticas.length > 0)
    ? p.alergias_criticas.map(a => `<span class="allergy-tag-urgent">⚠️ ${escapeHtml(a)}</span>`).join(' ')
    : '<span style="color:#059669; font-weight:600;">Sin alergias documentadas</span>';

  const medHtml = (p.medicacion_activa && p.medicacion_activa.length > 0)
    ? p.medicacion_activa.map(m => `<span class="med-tag-active">💊 ${escapeHtml(m)}</span>`).join(' ')
    : '<span style="color:#64748b;">Sin medicación activa registrada</span>';

  const dxHtml = (p.diagnosticos_clave && p.diagnosticos_clave.length > 0)
    ? p.diagnosticos_clave.map(d => `<span class="dx-tag-key">🩻 ${escapeHtml(d)}</span>`).join(' ')
    : '<span style="color:#64748b;">Sin diagnósticos crónicos reportados</span>';

  const nodesHtml = hospList.map(h => {
    return `
      <div class="hosp-record-pill">
        <span class="hr-icon">🏥</span>
        <div class="hr-content">
          <strong>${escapeHtml(h.hospital_nombre)}</strong>
          <span class="hr-sub">${escapeHtml(h.expediente_tipo)} • Act. ${escapeHtml(h.ultima_actualizacion)}</span>
        </div>
        <span class="hr-badge-clues">${escapeHtml(h.clues)}</span>
      </div>
    `;
  }).join('');

  area.innerHTML = `
    <div class="network-patient-card">
      <!-- Encabezado del paciente -->
      <div class="net-pat-header">
        <div class="net-pat-avatar">
          ${escapeHtml((p.nombre || 'P').substring(0, 2).toUpperCase())}
        </div>
        <div class="net-pat-main-info">
          <div class="net-pat-name-row">
            <h3>${escapeHtml(p.nombre)}</h3>
            <span class="blood-group-badge">🩸 Sangre: ${escapeHtml(p.tipo_sangre || 'N/D')}</span>
            <span class="privacy-seal-badge">${escapeHtml(priv.nivel || 'Safe Harbor Activo')}</span>
          </div>
          <div class="net-pat-curp-row">
            <span>CURP: <strong>${escapeHtml(p.curp)}</strong></span>
            <span>• Contacto de Emergencia: <strong>${escapeHtml(p.contacto_emergencia || 'No registrado')}</strong></span>
          </div>
        </div>
        <div class="net-pat-actions">
          <button type="button" class="btn-dark-pill" onclick="prepareReferralForPatient('${escapeHtml(p.curp)}', '${escapeHtml(p.nombre)}')">🚑 Iniciar Referencia NOM-004</button>
          <button type="button" class="btn-outline-pill" onclick="downloadFhirBundleForPatient('${escapeHtml(p.curp)}')">📦 Descargar Bundle FHIR R4</button>
        </div>
      </div>

      <!-- Cuadrícula de salvaguarda clínica -->
      <div class="net-pat-grid">
        <div class="net-info-box alert-box">
          <div class="nib-label">ALERGIAS MORTALES & CONTRAINDICACIONES</div>
          <div class="nib-content">${alergiasHtml}</div>
        </div>
        <div class="net-info-box">
          <div class="nib-label">MEDICACIÓN EN CURSO (RIESGO DE INTERACCIÓN)</div>
          <div class="nib-content">${medHtml}</div>
        </div>
        <div class="net-info-box">
          <div class="nib-label">DIAGNÓSTICOS CLAVE & ANTECEDENTES RELEVANTES</div>
          <div class="nib-content">${dxHtml}</div>
        </div>
      </div>

      <!-- Hospitales donde tiene expediente -->
      <div class="net-connected-hospitals-section">
        <div class="nch-header">
          <strong>HOSPITALES CON EXPEDIENTE CLÍNICO (${hospList.length} Nodos Localizados):</strong>
          <span style="font-size:12px; color:#64748b;">Protocolo Federado: Datos protegidos bajo custodia del hospital emisor</span>
        </div>
        <div class="nch-list">
          ${nodesHtml}
        </div>
      </div>

      <!-- Garantía de Privacidad Safe Harbor -->
      <div class="net-privacy-guarantee-bar">
        <span>🔒 <strong>Garantía de Privacidad MedicAItion:</strong> ${isUrg ? 'En modo Urgencias, notas privadas y psicoterapia han sido omitidas de la divulgación.' : 'Interconsulta autorizada con consentimiento informado.'}</span>
        <span class="hmac-tag">Sello Digital: ${escapeHtml((priv.sello_criptografico || '').substring(0, 24))}...</span>
      </div>
    </div>
  `;
}

function openNewReferralFormModal() {
  const modal = document.getElementById('modal-new-referral');
  if (modal) modal.style.display = 'flex';
}

function closeNewReferralModal() {
  const modal = document.getElementById('modal-new-referral');
  if (modal) modal.style.display = 'none';
}

function prepareReferralForPatient(curp, name) {
  openNewReferralFormModal();
  const curpInput = document.getElementById('ref-pat-curp');
  const nameInput = document.getElementById('ref-pat-name');
  if (curpInput) curpInput.value = curp;
  if (nameInput) nameInput.value = name;
}

async function submitNewReferralForm(e) {
  e.preventDefault();
  const curp = document.getElementById('ref-pat-curp')?.value;
  const nombre = document.getElementById('ref-pat-name')?.value;
  const hospSelect = document.getElementById('ref-hospital-destino')?.value;
  const prioridad = document.getElementById('ref-prioridad')?.value || 'Ordinaria';
  const cie10 = document.getElementById('ref-cie10')?.value;
  const motivo = document.getElementById('ref-motivo')?.value;
  const detalles = document.getElementById('ref-detalles')?.value;

  if (!curp || !nombre || !hospSelect || !cie10 || !motivo) {
    if (typeof showToast === 'function') showToast('Por favor complete los campos obligatorios (*)', 'error');
    return;
  }

  const [cluesDest, nombreDest] = hospSelect.split('|');

  try {
    const res = await fetch('/api/institutions/referrals', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patient_curp: curp,
        patient_nombre: nombre,
        clues_origen: 'YUC-CR-001',
        hospital_origen_nombre: 'Cruz Roja Mexicana Delegación Mérida',
        clues_destino: cluesDest,
        hospital_destino_nombre: nombreDest,
        motivo_envio: motivo,
        diagnostico_cie10: cie10,
        prioridad: prioridad,
        medico_solicitante: 'Dr. Roberto Morales',
        cedula_solicitante: 'CED-9482710',
        detalles_clinicos: detalles
      })
    });

    if (res.ok) {
      const data = await res.json();
      closeNewReferralModal();
      if (typeof showToast === 'function') {
        showToast(`Orden de referencia ${data.id} transmitida con éxito a ${nombreDest}`, 'success');
      }
      await loadReferralsTable();
      await loadAuditsTable();
    } else {
      if (typeof showToast === 'function') showToast('Error al transmitir la referencia hospitalaria', 'error');
    }
  } catch (err) {
    console.error('Error al emitir referencia:', err);
    if (typeof showToast === 'function') showToast('Fallo de conexión al emitir referencia', 'error');
  }
}

async function updateReferralState(refId, newStatus) {
  if (!newStatus) return;
  try {
    const res = await fetch(`/api/institutions/referrals/${encodeURIComponent(refId)}/status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ estado: newStatus })
    });
    if (res.ok) {
      if (typeof showToast === 'function') {
        showToast(`Referencia ${refId} actualizada a "${newStatus}"`, 'info');
      }
      await loadReferralsTable();
    }
  } catch (err) {
    console.error('Error al actualizar estado:', err);
  }
}

async function downloadFhirBundleForPatient(curp) {
  try {
    if (typeof showToast === 'function') showToast('Generando Bundle HL7 FHIR R4 interoperable...', 'info');
    const res = await fetch(`/api/patients/${encodeURIComponent(curp)}/fhir`);
    if (res.ok) {
      const bundle = await res.json();
      const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `FHIR_BUNDLE_${curp}.json`;
      a.click();
      URL.revokeObjectURL(url);
      if (typeof showToast === 'function') showToast('Bundle HL7 FHIR R4 descargado correctamente', 'success');
    } else {
      if (typeof showToast === 'function') showToast('No se encontró expediente exportable para esta CURP', 'error');
    }
  } catch (e) {
    console.error('Error al descargar FHIR:', e);
  }
}
"""

with open(JS_PATH, "r", encoding="utf-8") as f:
    js = f.read()

# 1. Actualizar switchMainTab para incluir 'red-hospitalaria'
if "nav-btn-red-hospitalaria" not in js:
    # Buscar const btnDash = document.getElementById('nav-btn-dashboard');
    anchor = "const btnLegal = document.getElementById('nav-btn-legal');"
    if anchor in js:
        js = js.replace(anchor, anchor + "\n  const btnRedHosp = document.getElementById('nav-btn-red-hospitalaria');", 1)
    
    anchor_toggle = "if (btnLegal) btnLegal.classList.toggle('active', tab === 'legal');"
    if anchor_toggle in js:
        js = js.replace(anchor_toggle, anchor_toggle + "\n  if (btnRedHosp) btnRedHosp.classList.toggle('active', tab === 'red-hospitalaria');", 1)

    anchor_panels = "'legal': { id: 'panel-legal-section', display: 'block', init: () => typeof loadLegalView === 'function' && loadLegalView() }"
    if anchor_panels in js:
        js = js.replace(anchor_panels, anchor_panels + ",\n    'red-hospitalaria': { id: 'panel-red-hospitalaria-section', display: 'block', init: () => typeof initRedHospitalariaView === 'function' && initRedHospitalariaView() }", 1)
    print("switchMainTab actualizado para red-hospitalaria.")

# 2. Agregar la lógica al final de app.js si no está presente
if "initRedHospitalariaView" not in js:
    js += "\n" + JS_LOGIC
    print("Lógica JS de Red Hospitalaria agregada.")

with open(JS_PATH, "w", encoding="utf-8") as f:
    f.write(js)

# Sincronizar a Linux_Ver
if os.path.exists(LINUX_JS):
    with open(LINUX_JS, "w", encoding="utf-8") as f:
        f.write(js)
    print("Sincronizado a Linux_Ver/frontend/app.js")

print("Listo app.js.")
