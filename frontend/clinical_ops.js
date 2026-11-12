/**
 * clinical_ops.js — MedicAItion v5.3 (Sprint 2)
 * ==========================================================
 * Operación clínica diaria conectada a datos reales (SQLite):
 *   • Dashboard vivo: siguiente paciente, KPIs, cola del día, tareas accionables
 *   • Vigilancia epidemiológica real (CIE-10)
 *   • Wearables: Web Bluetooth (Heart Rate 0x180D), importación CSV/JSON, captura manual
 *   • Reportes y Estadísticas + exportación CSV
 *   • Atajos de teclado para el médico
 *
 * Se carga DESPUÉS de app.js: las funciones aquí definidas reemplazan
 * a los prototipos estáticos anteriores (openWearableModal, importWearableHealthData, etc.).
 */

const TRIAGE_LABEL = { ROJO: 'Riesgo vital', NARANJA: 'Emergencia', AMARILLO: 'Urgencia', VERDE: 'Estable' };
const OpsState = {
  todayQueue: null,
  epi: null,
  summary: null,
  latestVitals: [],
  ble: { device: null, characteristic: null, lastSaved: 0, lastHr: null },
};

function _opsEsc(str) {
  if (str === null || str === undefined) return '';
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function _fmt12(t) {
  if (!t || !t.includes(':')) return t || '';
  const [h, m] = t.split(':');
  let hh = parseInt(h, 10);
  const ap = hh >= 12 ? 'PM' : 'AM';
  hh = hh % 12 || 12;
  return { time: `${String(hh).padStart(2, '0')}:${m}`, ampm: ap };
}

async function _getJson(url) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

/* ═══════════════════════════ DASHBOARD ═══════════════════════════ */

function refreshDashboard() {
  _renderGreeting();
  refreshDashboardAgenda();
  refreshDashboardTasks();
  refreshEpidemiology();
  refreshWearablesCard();
}

function _renderGreeting() {
  const h = new Date().getHours();
  const saludo = h < 12 ? 'Buenos días' : h < 19 ? 'Buenas tardes' : 'Buenas noches';
  const t = document.getElementById('dashboard-greeting-title');
  if (t) t.textContent = `${saludo}, Roberto`;
  const s = document.getElementById('dashboard-greeting-sub');
  if (s) {
    const fecha = new Date().toLocaleDateString('es-MX', { weekday: 'long', day: 'numeric', month: 'long' });
    s.textContent = `${fecha.charAt(0).toUpperCase() + fecha.slice(1)} — Resumen de tu actividad clínica.`;
  }
}

async function refreshDashboardAgenda() {
  const listEl = document.getElementById('dashboard-agenda-list');
  try {
    const q = await _getJson(`${API}/api/appointments/today`);
    OpsState.todayQueue = q;

    _setText('kpi-pendientes', q.pendientes);
    _setText('kpi-sala', q.en_sala);
    _setText('kpi-criticos', q.criticos);
    _setText('kpi-atendidas', q.atendidas);
    const critTile = document.querySelector('.kpi-tile-alert');
    if (critTile) critTile.classList.toggle('has-critical', q.criticos > 0);

    const caption = document.getElementById('dashboard-agenda-caption');
    if (caption) caption.textContent = `${q.total} cita${q.total === 1 ? '' : 's'} hoy • ordenadas por prioridad`;

    _renderNextPatient(q.items);

    if (!listEl) return;
    const active = q.items.filter(i => !['Atendida', 'No asistió'].includes(i.status));
    if (!active.length) {
      listEl.innerHTML = `
        <div class="agenda-empty-state">
          <p>✅ No hay pacientes pendientes hoy.</p>
          <button class="btn-dark-pill" onclick="openAppointmentModal()">+ Agendar cita</button>
        </div>`;
      return;
    }
    listEl.innerHTML = active.slice(0, 5).map(a => {
      const t = _fmt12(a.time);
      const tri = (a.triage || 'VERDE').toLowerCase();
      const isInConsult = a.status === 'En Consulta';
      const inSala = a.status === 'En Sala / Triaje';
      return `
        <div class="agenda-item">
          <div class="agenda-time"><span>${t.time}</span><small>${t.ampm}</small></div>
          <div class="agenda-pill-card triage-edge-${tri}">
            <div class="agenda-patient-info">
              <div class="agenda-patient-title">
                ${_opsEsc(a.patientName)}
                <span class="triage-mini triage-mini-${tri}">${_opsEsc(a.triage)}</span>
              </div>
              <div class="agenda-patient-sub">
                <span class="status-chip status-${inSala ? 'sala' : isInConsult ? 'consulta' : 'prog'}">${_opsEsc(a.status)}</span>
                <span class="agenda-dot-sep">&bull;</span>
                <span>${_opsEsc(a.reason)}</span>
              </div>
            </div>
            ${a.wearable ? `<div class="agenda-watch-badge watch-green" title="${_opsEsc(a.wearableText || 'Wearable vinculado')}">⌚</div>` : ''}
            <div class="agenda-actions-inline">
              ${!inSala && !isInConsult ? `<button class="btn-outline-pill btn-xs" onclick="markArrived('${a.id}')" title="Marcar llegada a sala">Llegó</button>` : ''}
              <button class="btn-dark-pill" onclick="startConsultationFromAppt('${a.id}')">${isInConsult ? 'Continuar' : 'Iniciar'}</button>
            </div>
          </div>
        </div>`;
    }).join('') + (active.length > 5 ? `<button class="agenda-see-all" onclick="switchMainTab('agenda')">Ver los ${active.length} pacientes ›</button>` : '');
  } catch (e) {
    if (listEl) listEl.innerHTML = '<div class="agenda-empty-state"><p>No se pudo cargar la agenda (servidor sin conexión).</p></div>';
  }
}

function _renderNextPatient(items) {
  const body = document.getElementById('next-patient-body');
  if (!body) return;
  const next = (items || []).find(i => ['En Consulta', 'En Sala / Triaje', 'Programada'].includes(i.status));
  if (!next) {
    body.innerHTML = `<span class="next-patient-empty">Sin pacientes en espera 🎉</span>
      <button class="btn-outline-pill btn-xs" onclick="openAppointmentModal()">+ Agendar</button>`;
    return;
  }
  const tri = (next.triage || 'VERDE').toLowerCase();
  const t = _fmt12(next.time);
  body.innerHTML = `
    <div class="next-patient-info">
      <div class="next-patient-name">${_opsEsc(next.patientName)} <span class="triage-mini triage-mini-${tri}">${_opsEsc(next.triage)}</span></div>
      <div class="next-patient-sub">${t.time} ${t.ampm} • ${_opsEsc(next.reason)} • <em>${_opsEsc(next.status)}</em></div>
    </div>
    <div class="next-patient-actions">
      ${next.curp ? `<button class="btn-outline-pill btn-xs" onclick="openPatientProfile('${_opsEsc(next.curp)}')">Expediente</button>` : ''}
      <button class="btn-red-cta" onclick="startConsultationFromAppt('${next.id}')">${next.status === 'En Consulta' ? 'Continuar ▶' : 'Atender ahora ▶'}</button>
    </div>`;
}

async function markArrived(apptId) {
  if (typeof updateAppointmentField === 'function') {
    const res = await updateAppointmentField(apptId, { status: 'En Sala / Triaje' });
    if (res) showToast(`${res.patientName} registrado en sala de espera`, 'success');
  }
}

function _setText(id, val) {
  const el = document.getElementById(id);
  if (el) el.textContent = (val === undefined || val === null) ? '—' : val;
}

async function refreshDashboardTasks() {
  const el = document.getElementById('dashboard-tasks-list');
  if (!el) return;
  try {
    const data = await _getJson(`${API}/api/analytics/tasks`);
    if (!data.tasks.length) {
      el.innerHTML = '<div class="task-item"><span class="task-icon task-done">✓</span><span class="task-text">Sin pendientes. Todo al día.</span></div>';
      return;
    }
    OpsState.tasks = data.tasks;
    el.innerHTML = data.tasks.slice(0, 5).map((t, idx) => {
      const cls = t.priority === 'CRITICA' ? 'task-crit' : t.priority === 'ALTA' ? 'task-alert' : 'task-info';
      const icon = t.priority === 'CRITICA' ? '!' : t.priority === 'ALTA' ? '!' : 'i';
      return `
        <div class="task-item" onclick="runTaskAction(${idx})" title="${_opsEsc(t.detail)}">
          <span class="task-icon ${cls}">${icon}</span>
          <span class="task-text">
            <strong>${_opsEsc(t.title)}</strong>
            <small>${_opsEsc(t.detail)}</small>
          </span>
        </div>`;
    }).join('');
  } catch {
    el.innerHTML = '<div class="task-item"><span class="task-icon task-alert">!</span><span class="task-text">No se pudieron cargar las tareas</span></div>';
  }
}

function runTaskAction(idx) {
  const t = (OpsState.tasks || [])[idx];
  if (!t || !t.action) return;
  const a = t.action;
  if (a.kind === 'start_appt' && a.id) startConsultationFromAppt(a.id);
  else if (a.kind === 'open_profile' && a.curp) openPatientProfile(a.curp);
  else if (a.kind === 'goto' && a.tab) switchMainTab(a.tab);
}

async function refreshEpidemiology() {
  try {
    const epi = await _getJson(`${API}/api/analytics/epidemiology`);
    OpsState.epi = epi;
    const top = epi.top_alert;
    const topicEl = document.getElementById('epi-topic');
    const badge = document.getElementById('epi-live-badge');
    if (!top) {
      if (topicEl) topicEl.innerHTML = 'Sin casos agrupados aún —<br/>se calcula con cada consulta';
      _setText('epi-stat-share', '0%');
      _setText('epi-stat-change', '0%');
      _setText('epi-stat-share-lbl', 'De consultas');
      _setText('epi-stat-change-lbl', 'vs semana previa');
    } else {
      if (topicEl) topicEl.innerHTML = `${_opsEsc(top.label)} —<br/>${top.this_week} caso(s) esta semana`;
      _setText('epi-stat-share', `${top.share_pct}%`);
      _setText('epi-stat-change', `${top.change_pct > 0 ? '+' : ''}${top.change_pct}%`);
      _setText('epi-stat-share-lbl', 'De consultas');
      _setText('epi-stat-change-lbl', 'vs semana previa');
      if (badge) {
        badge.textContent = top.alert_level === 'ALTA' ? 'Alerta ALTA' : 'En tiempo real';
        badge.classList.toggle('epi-badge-high', top.alert_level === 'ALTA');
      }
    }
    const mini = document.getElementById('epi-mini-list');
    if (mini) {
      const rows = epi.groups.filter(g => g.total > 0).slice(0, 3);
      mini.innerHTML = rows.length
        ? rows.map(g => `<div class="epi-mini-row"><span>${_opsEsc(g.label)}</span><strong>${g.total}</strong></div>`).join('')
        : `<div class="epi-mini-row"><span>Consultas analizadas</span><strong>${epi.total_consultas}</strong></div>`;
    }
  } catch { /* deja valores previos */ }
}

/* ═══════════════════════════ WEARABLES ═══════════════════════════ */

async function refreshWearablesCard() {
  try {
    const latest = await _getJson(`${API}/api/wearables/latest`);
    OpsState.latestVitals = latest;
    const list = document.getElementById('connected-devices-list');
    if (list) {
      list.innerHTML = latest.slice(0, 3).map(r => `
        <div class="device-item ${r.alert ? 'device-alert' : ''}" onclick="${r.curp ? `openPatientProfile('${_opsEsc(r.curp)}')` : ''}">
          <div class="device-title">${_opsEsc(r.patientName || r.curp || 'Paciente')}</div>
          <div class="device-sub">(${_opsEsc(r.device)}) - ${r.alert
            ? `<span class="status-alert">⚠ ${_opsEsc(r.alert_message)}</span>`
            : `<span class="status-connected">FC ${r.heart_rate ?? '--'} • SpO2 ${r.spo2 ?? '--'}% ✅</span>`}</div>
        </div>`).join('') || '<div class="device-item"><div class="device-sub">Sin lecturas. Conecta un dispositivo.</div></div>';
    }
    const first = latest.find(r => r.heart_rate) || latest[0];
    if (first) {
      if (first.heart_rate) _setText('live-bpm-val', Math.round(first.heart_rate));
      if (first.spo2) _setText('live-spo2-val', `${Math.round(first.spo2)}%`);
    }
  } catch { /* offline */ }
}

async function _populateWearablePatients() {
  const sel = document.getElementById('wearable-patient-select');
  if (!sel) return;
  const prev = sel.value;
  try {
    const patients = await _getJson(`${API}/api/patients/`);
    sel.innerHTML = '<option value="">— Selecciona paciente —</option>' + patients.map(p => {
      const name = p.nombre || p.nombre_completo || p.curp;
      return `<option value="${_opsEsc(p.curp)}" data-name="${_opsEsc(name)}">${_opsEsc(name)} (${_opsEsc(p.curp)})</option>`;
    }).join('');
    const curpInput = document.getElementById('curp-input')?.value.trim().toUpperCase();
    sel.value = prev || curpInput || '';
  } catch { /* ignore */ }
}

function _selectedWearablePatient() {
  const sel = document.getElementById('wearable-patient-select');
  if (!sel || !sel.value) return { curp: '', name: '' };
  const opt = sel.options[sel.selectedIndex];
  return { curp: sel.value, name: opt?.dataset?.name || '' };
}

function openWearableModal(tab) {
  document.getElementById('wearable-modal-overlay')?.classList.add('open');
  setWearableTab(tab || 'ble');
  _populateWearablePatients();
  loadWearableLatest();
}

function closeWearableModal() {
  document.getElementById('wearable-modal-overlay')?.classList.remove('open');
}

function setWearableTab(tab) {
  ['ble', 'file', 'manual'].forEach(t => {
    document.getElementById(`wtab-${t}`)?.classList.toggle('active', t === tab);
    const pane = document.getElementById(`wpane-${t}`);
    if (pane) pane.style.display = t === tab ? 'block' : 'none';
  });
}

async function loadWearableLatest() {
  const el = document.getElementById('wearable-latest-list');
  if (!el) return;
  try {
    const latest = await _getJson(`${API}/api/wearables/latest`);
    OpsState.latestVitals = latest;
    el.innerHTML = latest.length ? latest.slice(0, 6).map(r => `
      <div class="llm-opt ${r.alert ? 'wearable-reading-alert' : ''}">
        <div class="llm-opt-body">
          <div class="llm-opt-title">⌚ ${_opsEsc(r.patientName || r.curp || 'Sin paciente')} — ${_opsEsc(r.device)} <small>(${_opsEsc(r.source)})</small></div>
          <div class="llm-opt-desc">
            FC: <strong>${r.heart_rate ?? '--'}</strong> lpm &bull; SpO2: <strong>${r.spo2 ?? '--'}%</strong>
            ${r.systolic_bp ? `&bull; TA: <strong>${r.systolic_bp}/${r.diastolic_bp ?? '--'}</strong>` : ''}
            ${r.temperature ? `&bull; Temp: <strong>${r.temperature} °C</strong>` : ''}
            &bull; ${new Date(r.recorded_at + 'Z').toLocaleString('es-MX', { dateStyle: 'short', timeStyle: 'short' })}
            ${r.alert ? `<div class="wearable-alert-line">⚠ ${_opsEsc(r.alert_message)}</div>` : ''}
          </div>
        </div>
      </div>`).join('') : '<div class="wearable-empty">Aún no hay lecturas registradas.</div>';
  } catch {
    el.innerHTML = '<div class="wearable-empty">Servidor no disponible.</div>';
  }
}

async function _postReading(payload) {
  const res = await fetch(`${API}/api/wearables/readings`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'No se pudo guardar la lectura');
  }
  return res.json();
}

/* ── Web Bluetooth: Heart Rate Service ── */
async function connectBleHeartRate() {
  if (!navigator.bluetooth) {
    showToast('Este navegador no soporta Web Bluetooth. Usa Chrome o Edge (en localhost o HTTPS).', 'error');
    return;
  }
  const p = _selectedWearablePatient();
  if (!p.curp) {
    showToast('Selecciona primero el paciente al que pertenece el sensor', 'error');
    return;
  }
  try {
    _bleStatus('Buscando dispositivos...', 'ble-status-wait');
    const device = await navigator.bluetooth.requestDevice({ filters: [{ services: ['heart_rate'] }] });
    device.addEventListener('gattserverdisconnected', () => {
      _bleStatus('● Desconectado', 'ble-status-idle');
      _toggleBleButtons(false);
    });
    const server = await device.gatt.connect();
    const service = await server.getPrimaryService('heart_rate');
    const ch = await service.getCharacteristic('heart_rate_measurement');
    await ch.startNotifications();
    ch.addEventListener('characteristicvaluechanged', (ev) => _onHeartRate(ev.target.value, device.name || 'Sensor BLE'));
    OpsState.ble = { device, characteristic: ch, lastSaved: 0, lastHr: null, patient: p };
    _setText('ble-device-name', `${device.name || 'Sensor BLE'} → ${p.name || p.curp}`);
    _bleStatus('● Conectado — recibiendo datos', 'ble-status-live');
    _toggleBleButtons(true);
    showToast(`Sensor ${device.name || ''} conectado`, 'success');
  } catch (e) {
    _bleStatus('● Desconectado', 'ble-status-idle');
    if (e && e.name !== 'NotFoundError') showToast(`Bluetooth: ${e.message}`, 'error');
  }
}

function _onHeartRate(dataView, deviceName) {
  const flags = dataView.getUint8(0);
  const hr = (flags & 0x01) ? dataView.getUint16(1, true) : dataView.getUint8(1);
  OpsState.ble.lastHr = hr;
  _setText('ble-live-hr', hr);
  _setText('live-bpm-val', hr);

  const now = Date.now();
  if (now - OpsState.ble.lastSaved > 15000) {
    OpsState.ble.lastSaved = now;
    const p = OpsState.ble.patient || {};
    _postReading({ curp: p.curp, patientName: p.name, device: deviceName, source: 'ble', heart_rate: hr })
      .then(r => {
        if (r.alert) showToast(`⚠ ${r.alert_message} — ${p.name || p.curp}`, 'error');
        refreshWearablesCard();
      })
      .catch(() => {});
  }
}

function disconnectBle() {
  try { OpsState.ble.device?.gatt?.disconnect(); } catch { /* ignore */ }
  _toggleBleButtons(false);
  _bleStatus('● Desconectado', 'ble-status-idle');
  loadWearableLatest();
}

function _bleStatus(text, cls) {
  const el = document.getElementById('ble-live-status');
  if (el) { el.textContent = text; el.className = cls; }
}

function _toggleBleButtons(connected) {
  const c = document.getElementById('ble-connect-btn');
  const d = document.getElementById('ble-disconnect-btn');
  if (c) c.style.display = connected ? 'none' : '';
  if (d) d.style.display = connected ? '' : 'none';
}

/* ── Importación de archivos CSV/JSON ── */
async function importWearableFile() {
  const p = _selectedWearablePatient();
  const input = document.getElementById('wearable-file-input');
  const out = document.getElementById('wearable-import-result');
  if (!p.curp) return showToast('Selecciona el paciente antes de importar', 'error');
  const file = input?.files?.[0];
  if (!file) return showToast('Selecciona un archivo CSV o JSON', 'error');

  const content = await file.text();
  const format = file.name.toLowerCase().endsWith('.json') ? 'json' : 'csv';
  try {
    const res = await fetch(`${API}/api/wearables/import`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ format, content, curp: p.curp, patientName: p.name, device: `Archivo ${file.name}` }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error de importación');
    if (out) {
      out.innerHTML = `<div class="import-ok">✅ ${data.imported} lectura(s) importadas${data.skipped ? `, ${data.skipped} omitidas` : ''}.</div>
        ${data.total_alerts ? `<div class="import-warn">⚠ ${data.total_alerts} lectura(s) fuera de rango: ${data.alerts.map(_opsEsc).join(' | ')}</div>` : ''}`;
    }
    showToast(`${data.imported} lecturas importadas`, 'success');
    loadWearableLatest();
    refreshWearablesCard();
    refreshDashboardTasks();
  } catch (e) {
    if (out) out.innerHTML = `<div class="import-warn">❌ ${_opsEsc(e.message)}</div>`;
    showToast(e.message, 'error');
  }
}

function downloadWearableTemplate() {
  const csv = 'timestamp,heart_rate,spo2,systolic,diastolic,temperature,steps\n' +
    '2026-11-11T08:00:00,72,98,122,78,36.5,1200\n' +
    '2026-11-11T12:00:00,88,97,128,82,36.8,4300\n';
  const blob = new Blob([csv], { type: 'text/csv' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'plantilla_signos_vitales_medicaition.csv';
  a.click();
  URL.revokeObjectURL(a.href);
}

/* ── Captura manual de triaje ── */
async function saveManualVitals() {
  const p = _selectedWearablePatient();
  if (!p.curp) return showToast('Selecciona el paciente', 'error');
  const v = id => document.getElementById(id)?.value;
  const payload = {
    curp: p.curp, patientName: p.name, device: 'Captura manual (triaje)', source: 'manual',
    heart_rate: v('mv-hr'), spo2: v('mv-spo2'), systolic_bp: v('mv-sys'), diastolic_bp: v('mv-dia'), temperature: v('mv-temp'),
  };
  try {
    const r = await _postReading(payload);
    const glu = v('mv-glu');
    OpsState.manualGlucose = glu ? { curp: p.curp, value: glu } : null;
    showToast(r.alert ? `⚠ Guardado con alerta: ${r.alert_message}` : 'Signos vitales guardados', r.alert ? 'error' : 'success');
    ['mv-hr', 'mv-spo2', 'mv-sys', 'mv-dia', 'mv-temp', 'mv-glu'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
    loadWearableLatest();
    refreshWearablesCard();
    refreshDashboardTasks();
  } catch (e) {
    showToast(e.message, 'error');
  }
}

/* ── Integración con la consulta ── */
async function fetchLatestVitalsText(curp) {
  if (!curp) return '';
  try {
    const rows = await _getJson(`${API}/api/wearables/readings?curp=${encodeURIComponent(curp)}&limit=1`);
    const r = rows[rows.length - 1];
    if (!r) return '';
    const parts = [];
    if (r.systolic_bp) parts.push(`TA ${Math.round(r.systolic_bp)}/${Math.round(r.diastolic_bp || 0)} mmHg`);
    if (r.heart_rate) parts.push(`FC ${Math.round(r.heart_rate)} lpm`);
    if (r.spo2) parts.push(`SpO2 ${Math.round(r.spo2)}%`);
    if (r.temperature) parts.push(`Temp ${r.temperature} °C`);
    if (OpsState.manualGlucose && OpsState.manualGlucose.curp === curp) parts.push(`Glucosa ${OpsState.manualGlucose.value} mg/dL`);
    if (!parts.length) return '';
    const when = new Date(r.recorded_at + 'Z').toLocaleString('es-MX', { dateStyle: 'short', timeStyle: 'short' });
    return `Signos vitales (${r.device}, ${when}): ${parts.join(', ')}.`;
  } catch {
    return '';
  }
}

async function importWearableHealthData() {
  const p = _selectedWearablePatient();
  const curp = p.curp || document.getElementById('curp-input')?.value.trim().toUpperCase();
  if (!curp) {
    showToast('Selecciona un paciente para importar sus signos vitales', 'error');
    return;
  }
  const text = await fetchLatestVitalsText(curp);
  if (!text) {
    showToast('Este paciente no tiene lecturas registradas aún', 'info');
    return;
  }
  switchMainTab('consulta');
  setMode('text');
  const curpEl = document.getElementById('curp-input');
  if (curpEl) curpEl.value = curp;
  const txtEl = document.getElementById('text-input');
  if (txtEl) txtEl.value = `${text} ${txtEl.value || ''}`.trim();
  showToast('Signos vitales insertados en la consulta', 'success');
}

function startBlankConsultation() {
  AppState.activeAppointmentId = null;
  switchMainTab('consulta');
  setTimeout(() => document.getElementById('curp-input')?.focus(), 50);
}

/* ═══════════════════════════ REPORTES ═══════════════════════════ */

async function renderReportsView() {
  const kpiEl = document.getElementById('reports-kpi-grid');
  try {
    const [summary, epi] = await Promise.all([
      _getJson(`${API}/api/analytics/summary`),
      _getJson(`${API}/api/analytics/epidemiology?weeks=8`),
    ]);
    OpsState.summary = summary;
    OpsState.epi = epi;

    const kpis = [
      ['Pacientes registrados', summary.pacientes],
      ['Consultas (30 días)', summary.consultas_30d],
      ['Citas hoy', `${summary.atendidas_hoy}/${summary.citas_hoy}`],
      ['Inasistencia', `${summary.tasa_inasistencia_pct}%`],
      ['Alertas biométricas', summary.alertas_biometricas],
      ['Alergias registradas', summary.alergias_registradas],
    ];
    if (kpiEl) kpiEl.innerHTML = kpis.map(([l, v]) => `
      <div class="reports-kpi"><span class="reports-kpi-val">${_opsEsc(v)}</span><span class="reports-kpi-lbl">${_opsEsc(l)}</span></div>`).join('');

    const tableEl = document.getElementById('reports-epi-table');
    if (tableEl) {
      const maxVal = Math.max(1, ...epi.groups.flatMap(g => g.series));
      tableEl.innerHTML = `
        <div class="epi-row epi-row-head"><span>Grupo</span><span>Tendencia 8 sem.</span><span>Semana</span><span>Cambio</span><span>Nivel</span></div>
        ${epi.groups.map(g => `
          <div class="epi-row">
            <span>${_opsEsc(g.label)}</span>
            <span class="sparkbars">${g.series.map(v => `<i style="height:${Math.max(2, Math.round((v / maxVal) * 26))}px" title="${v}"></i>`).join('')}</span>
            <span><strong>${g.this_week}</strong> <small>/ ${g.total}</small></span>
            <span class="${g.change_pct > 0 ? 'chg-up' : g.change_pct < 0 ? 'chg-down' : ''}">${g.change_pct > 0 ? '+' : ''}${g.change_pct}%</span>
            <span class="epi-level epi-level-${g.alert_level.toLowerCase()}">${g.alert_level}</span>
          </div>`).join('')}
        <p class="reports-footnote">Fuente: ${_opsEsc(epi.fuente)} • ${epi.total_consultas} consultas analizadas.</p>`;
    }

    const triEl = document.getElementById('reports-triage-bars');
    if (triEl) {
      const tri = summary.triaje_hoy;
      const total = Math.max(1, Object.values(tri).reduce((a, b) => a + b, 0));
      triEl.innerHTML = Object.entries(tri).map(([k, v]) => `
        <div class="rbar-row">
          <span class="triage-mini triage-mini-${k.toLowerCase()}">${k}</span>
          <div class="rbar-track"><div class="rbar-fill rbar-${k.toLowerCase()}" style="width:${Math.round((v / total) * 100)}%"></div></div>
          <strong>${v}</strong>
        </div>`).join('');
    }

    const dxEl = document.getElementById('reports-top-dx');
    if (dxEl) {
      dxEl.innerHTML = summary.top_diagnosticos.length
        ? summary.top_diagnosticos.map(d => `<div class="topdx-row"><span>${_opsEsc(d.label)}</span><strong>${d.count}</strong></div>`).join('')
        : '<p class="reports-footnote">Aún no hay consultas con códigos CIE-10 registradas.</p>';
    }
  } catch (e) {
    if (kpiEl) kpiEl.innerHTML = '<p class="reports-footnote">No se pudieron cargar los reportes (servidor sin conexión).</p>';
  }
}

function exportReportsCsv() {
  const epi = OpsState.epi;
  if (!epi) return showToast('Primero carga el reporte', 'info');
  const lines = ['grupo,casos_semana,casos_semana_previa,cambio_pct,total_8_semanas,porcentaje_consultas,nivel_alerta'];
  epi.groups.forEach(g => lines.push([`"${g.label}"`, g.this_week, g.prev_week, g.change_pct, g.total, g.share_pct, g.alert_level].join(',')));
  const blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `vigilancia_epidemiologica_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}

/* Compatibilidad con botones existentes */
function focusEpidemiologiaSection() { switchMainTab('reportes'); }

/* ═══════════════════════════ ATAJOS DE TECLADO ═══════════════════════════ */
document.addEventListener('keydown', (e) => {
  const tag = (e.target && e.target.tagName) || '';
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault();
    document.getElementById('global-quick-search')?.focus();
    return;
  }
  if (!e.altKey || ['INPUT', 'TEXTAREA', 'SELECT'].includes(tag)) return;
  const k = e.key.toLowerCase();
  if (k === 'n') { e.preventDefault(); startBlankConsultation(); }
  else if (k === 'a') { e.preventDefault(); openAppointmentModal(); }
  else if (k === 'p') { e.preventDefault(); switchMainTab('expedientes'); }
  else if (k === 'h') { e.preventDefault(); switchMainTab('dashboard'); }
  else if (k === 'c') { e.preventDefault(); switchMainTab('agenda'); }
});

/* Refresco automático del tablero cada 60 s mientras está visible */
setInterval(() => {
  if (AppState.mainTab === 'dashboard' && !document.hidden) {
    refreshDashboardAgenda();
    refreshDashboardTasks();
  }
}, 60000);


/* ═══════════════════════════ PLANTILLAS RÁPIDAS Y CALCULADORAS ═══════════════════════════ */

const CLINICAL_TEMPLATES = {
  dm2: 'Paciente en control crónico de Diabetes Mellitus tipo 2 e Hipertensión Arterial. Refiere apego parcial a dieta, sin mareos ni visión borrosa. Signos vitales: TA 132/82 mmHg, FC 76 lpm, FR 16 rpm, Temp 36.5 °C, SpO2 98%, Glucosa capilar 148 mg/dL. Exploración cardiopulmonar normal, extremidades sin edema. Se indica continuar Metformina 850 mg cada 12 horas y Losartán 50 mg cada 24 horas, además de química sanguínea y HbA1c.',
  dengue: 'Paciente masculino con cuadro febril de 3 días de evolución (Temp 39.1 °C), dolor retroocular, mialgias y artralgias intensas. Refiere dolor abdominal intenso hoy y leve sangrado de encías. TA 98/64 mmHg, FC 114 lpm, FR 22 rpm, SpO2 97%. Sospecha de Dengue con signos de alarma. Se indica Paracetamol 500 mg cada 8 horas por 3 días, hidratación oral/IV inmediata y biometría hemática urgente.',
  resp: 'Paciente acude por tos productiva, odinofagia y rinorrea de 4 días de evolución, acompañadas de febrícula. TA 118/76 mmHg, FC 84 lpm, FR 18 rpm, Temp 37.6 °C, SpO2 97%. Faringe hiperémica, campos pulmonares bien ventilados sin estertores. Se indica Paracetamol 500 mg cada 8 horas por 4 días y medidas generales.',
  toracico: 'Paciente masculino de 56 años acude a urgencias por dolor en el pecho opresivo de inicio súbito hace 30 minutos irradiado al brazo izquierdo, acompañado de diaforesis fría y falta de aire. TA 94/60 mmHg, FC 122 lpm, FR 24 rpm, SpO2 89%. Probable Síndrome Coronario Agudo. Se activa Código Infarto.'
};

function applyClinicalTemplate(key) {
  const tpl = CLINICAL_TEMPLATES[key];
  if (!tpl) return;
  setMode('text');
  const txtEl = document.getElementById('text-input');
  if (txtEl) {
    txtEl.value = tpl;
    txtEl.focus();
  }
  showToast('Plantilla clínica aplicada — puedes editar o dictar encima', 'info');
}

function openCalculatorsModal() {
  document.getElementById('calculators-modal-overlay')?.classList.add('open');
  calcClinicalTools();
}

function closeCalculatorsModal() {
  document.getElementById('calculators-modal-overlay')?.classList.remove('open');
}

function calcClinicalTools() {
  const peso = parseFloat(document.getElementById('calc-peso')?.value);
  const talla = parseFloat(document.getElementById('calc-talla')?.value);
  const tas = parseFloat(document.getElementById('calc-tas')?.value);
  const tad = parseFloat(document.getElementById('calc-tad')?.value);
  const out1 = document.getElementById('calc-imc-pam-out');
  if (out1) {
    const parts = [];
    if (peso > 0 && talla > 0) {
      const imc = peso / ((talla / 100) ** 2);
      const cat = imc < 18.5 ? 'Bajo peso' : imc < 25 ? 'Normal' : imc < 30 ? 'Sobrepeso' : 'Obesidad';
      parts.push(`<strong>IMC:</strong> ${imc.toFixed(1)} kg/m² (${cat})`);
    }
    if (tas > 0 && tad > 0) {
      const pam = (tas + 2 * tad) / 3;
      const pamTag = pam < 65 ? '⚠ Hipoperfusión (<65)' : pam > 110 ? '⚠ Elevada' : 'Normal (70–100)';
      parts.push(`<strong>PAM:</strong> ${pam.toFixed(1)} mmHg (${pamTag})`);
    }
    out1.innerHTML = parts.length ? parts.join(' &bull; ') : 'Ingresa peso/talla o presión para calcular al instante.';
  }

  const pPed = parseFloat(document.getElementById('calc-ped-peso')?.value);
  const mgkg = parseFloat(document.getElementById('calc-ped-mgkg')?.value);
  const tomas = Math.max(1, parseInt(document.getElementById('calc-ped-tomas')?.value || '3', 10));
  const out2 = document.getElementById('calc-ped-out');
  if (out2) {
    if (pPed > 0 && mgkg > 0) {
      const totalDia = pPed * mgkg;
      const porToma = totalDia / tomas;
      out2.innerHTML = `<strong>Dosis total/día:</strong> ${totalDia.toFixed(0)} mg/día &bull; <strong>Cada toma (${tomas}x):</strong> ${porToma.toFixed(0)} mg cada ${Math.round(24 / tomas)} h`;
    } else {
      out2.textContent = 'Ingresa peso y mg/kg/día (ej. Paracetamol 45-60, Amoxicilina 40-90).';
    }
  }
}
