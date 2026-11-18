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
  const rawName = (window.AppState?.operatorProfile?.full_name || 'Dr. Roberto Morales').trim();
  const cleanFirst = rawName.replace(/^(Dr\.|Dra\.|Enf\.|Lic\.|Dir\.)\s*/i, '').split(/\s+/)[0] || rawName;
  const t = document.getElementById('dashboard-greeting-title');
  if (t) t.textContent = `${saludo}, ${cleanFirst}`;
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
      const visible = latest.slice(0, 2);
      const extra = latest.length > 2
        ? `<div class="device-more-link" onclick="openWearableModal()">+${latest.length - 2} dispositivo(s) más ›</div>`
        : '';
      list.innerHTML = visible.map(r => `
        <div class="device-item ${r.alert ? 'device-alert' : ''}" onclick="${r.curp ? `openPatientProfile('${_opsEsc(r.curp)}')` : ''}">
          <div class="device-title">${_opsEsc(r.patientName || r.curp || 'Paciente')}</div>
          <div class="device-sub">(${_opsEsc(r.device)}) - ${r.alert
            ? `<span class="status-alert">⚠ ${_opsEsc(r.alert_message)}</span>`
            : `<span class="status-connected">FC ${r.heart_rate ?? '--'} • SpO2 ${r.spo2 ?? '--'}% ✅</span>`}</div>
        </div>`).join('') + extra || '<div class="device-item"><div class="device-sub">Sin lecturas. Conecta un dispositivo.</div></div>';
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


/* ════════════════════════════════════════════════════════════════
   SPRINT 3 — HERRAMIENTAS IA, ASK-EXPEDIENTE, ICE, PORTAL & FHIR
   ════════════════════════════════════════════════════════════════ */

async function initHerramientasView() {
  await _populateToolsPatients();
  calcSuiteAll();
}

async function _populateToolsPatients(selectedCurp) {
  const sel = document.getElementById('ask-patient-select');
  if (!sel) return;
  const prev = selectedCurp || sel.value;
  try {
    const patients = await _getJson(`${API}/api/patients/`);
    sel.innerHTML = patients.map(p => {
      const name = p.nombre || p.nombre_completo || p.curp;
      return `<option value="${_opsEsc(p.curp)}">${_opsEsc(name)} (${_opsEsc(p.curp)})</option>`;
    }).join('') || '<option value="">Sin pacientes registrados</option>';
    if (prev && patients.some(p => p.curp === prev)) sel.value = prev;
  } catch { /* ignore */ }
}

function _selectedToolCurp() {
  return document.getElementById('ask-patient-select')?.value || '';
}

function setAskQuickQuestion(q) {
  const inp = document.getElementById('ask-question-input');
  if (inp) inp.value = q;
  askExpedienteQuery();
}

async function askExpedienteQuery() {
  const curp = _selectedToolCurp();
  const inp = document.getElementById('ask-question-input');
  const outBox = document.getElementById('ask-response-box');
  if (!curp) return showToast('Selecciona primero un paciente', 'error');
  const q = (inp?.value || '').trim() || 'Resumen clínico integral, alergias, medicamentos y riesgos';
  if (outBox) outBox.innerHTML = 'Consultando historial longitudinal y memoria vectorial...';
  try {
    const res = await fetch(`${API}/api/patients/${encodeURIComponent(curp)}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question: q, llm_mode: AppState?.llmMode || 'offline' }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error al consultar expediente');
    const cites = (data.citations || []).map(c =>
      `<span class="ask-cite-pill" title="${_opsEsc(c.detalle)}">📌 ${_opsEsc(c.fuente)}</span>`
    ).join('');
    if (outBox) {
      outBox.innerHTML = `<div>${_opsEsc(data.answer)}</div>`
        + (cites ? `<div class="ask-citations">${cites}</div>` : '');
    }
  } catch (e) {
    if (outBox) outBox.textContent = `No se pudo consultar: ${e.message}`;
  }
}

async function openAskForPatient(curp) {
  if (typeof OverlaySystem !== 'undefined') OverlaySystem.close();
  switchMainTab('herramientas');
  await _populateToolsPatients(curp);
  setAskQuickQuestion('Resumen clínico integral, alergias, medicamentos actuales y últimos signos vitales');
}

function downloadPatientFhir(curp) {
  const c = curp || _selectedToolCurp();
  if (!c) return showToast('Selecciona un paciente primero', 'error');
  window.open(`${API}/api/patients/${encodeURIComponent(c)}/fhir?download=true`, '_blank');
  showToast('Descargando Bundle HL7 FHIR R4 (NOM-024)...', 'success');
}

async function openIceModal(curp) {
  const c = curp || _selectedToolCurp();
  if (!c) return showToast('Selecciona un paciente primero', 'error');
  const overlay = document.getElementById('ice-modal-overlay');
  const body = document.getElementById('ice-modal-body');
  if (!overlay || !body) return;
  body.innerHTML = '<p>Generando Pasaporte Médico de Emergencia QR (ICE)...</p>';
  overlay.classList.add('open');
  try {
    const ice = await _getJson(`${API}/api/ice/${encodeURIComponent(c)}`);
    const allergies = (ice.alergias || []).length
      ? ice.alergias.map(a => `<div class="portal-log-row is-alert">⚠️ ${_opsEsc(a.descripcion)} (${_opsEsc(a.severidad)})</div>`).join('')
      : '<div class="portal-log-row">✅ Sin alergias críticas registradas</div>';
    const meds = (ice.medicamentos_actuales || []).length
      ? ice.medicamentos_actuales.map(m => `<li><strong>${_opsEsc(m.nombre)}</strong> ${_opsEsc(m.dosis)} (${_opsEsc(m.periodicidad)})</li>`).join('')
      : '<li>Sin medicación crónica registrada</li>';
    const iceUrl = `${window.location.origin}/ice/${encodeURIComponent(ice.curp)}`;
    body.innerHTML = `
      <div class="ice-preview-header">
        <div>
          <div style="font-size:11px;font-weight:800;letter-spacing:0.06em;opacity:0.9;">PASAPORTE DE EMERGENCIA (ICE) &bull; CRUZ ROJA MÉRIDA</div>
          <h3 style="margin:4px 0 2px;font-size:19px;">${_opsEsc(ice.nombre_completo)}</h3>
          <div style="font-size:12px;opacity:0.9;">${ice.edad ?? '—'} años &bull; ${_opsEsc(ice.sexo || '—')} &bull; CURP: ${_opsEsc(ice.curp)}</div>
        </div>
        <div class="ice-blood-tag"><div style="font-size:9px;color:#475569;text-transform:uppercase;">Sangre</div>${_opsEsc(ice.tipo_sangre)}</div>
      </div>
      <div class="ice-preview-grid">
        <div>
          <h4 style="margin:6px 0;">Alergias Críticas</h4>
          ${allergies}
          <h4 style="margin:10px 0 4px;">Medicación Actual</h4>
          <ul style="margin:0;padding-left:18px;font-size:12.5px;">${meds}</ul>
          <h4 style="margin:10px 0 4px;">Contacto de Emergencia</h4>
          <div style="font-size:13px;"><strong>${_opsEsc(ice.contacto_emergencia?.nombre)}</strong> &bull; ${_opsEsc(ice.contacto_emergencia?.telefono || 'Sin teléfono')}</div>
        </div>
        <div class="ice-qr-box">
          <img src="${API}/api/ice/${encodeURIComponent(ice.curp)}/qr" alt="QR Pasaporte ICE" style="width:150px;height:150px;" />
          <small style="font-size:10.5px;text-align:center;">Escanea para rescate en &lt;2s (sin notas privadas)</small>
        </div>
      </div>
      <div class="wearable-btn-row" style="margin-top:14px;">
        <a class="btn-red-cta" style="text-decoration:none;" href="${iceUrl}" target="_blank">🪪 Abrir Tarjeta ICE Imprimible</a>
        <button class="btn-outline-pill" onclick="navigator.clipboard?.writeText('${iceUrl}'); showToast('Enlace ICE copiado', 'success');">📋 Copiar enlace QR</button>
      </div>`;
  } catch (e) {
    body.innerHTML = `<p style="color:#dc2626;">Error cargando Pasaporte ICE: ${_opsEsc(e.message)}</p>`;
  }
}

function closeIceModal() {
  document.getElementById('ice-modal-overlay')?.classList.remove('open');
}

async function openPatientPortalModal(curp) {
  const c = curp || _selectedToolCurp();
  if (!c) return showToast('Selecciona un paciente primero', 'error');
  const overlay = document.getElementById('portal-modal-overlay');
  const body = document.getElementById('portal-modal-body');
  if (!overlay || !body) return;
  body.innerHTML = '<p>Cargando portal ciudadano "Mi Salud Hoy"...</p>';
  overlay.classList.add('open');
  try {
    const data = await _getJson(`${API}/api/patient-portal/${encodeURIComponent(c)}`);
    let slotsHtml = '';
    for (const [slot, items] of Object.entries(data.horario_visual || {})) {
      if (!items.length) continue;
      slotsHtml += `<div class="portal-slot-box"><h5>${_opsEsc(slot)}</h5><ul style="margin:0;padding-left:18px;font-size:12.5px;">${items.map(m =>
        `<li><strong>${_opsEsc(m.nombre)}</strong> — ${_opsEsc(m.dosis)} (${_opsEsc(m.duracion || 'según indicación')})</li>`
      ).join('')}</ul></div>`;
    }
    if (!slotsHtml) slotsHtml = '<div class="portal-slot-box">Sin medicamentos activos en la última consulta.</div>';

    const flags = (data.banderas_rojas || []).map(f => `<li>${_opsEsc(f)}</li>`).join('');
    const logs = (data.daily_logs || []).slice(0, 5).map(l => `
      <div class="portal-log-row ${l.alert_flag ? 'is-alert' : ''}">
        <strong>${_opsEsc((l.recorded_at || '').slice(0, 16).replace('T', ' '))}</strong> —
        TA ${l.systolic_bp ?? '--'}/${l.diastolic_bp ?? '--'} mmHg · Glucosa ${l.glucose_mg_dl ?? '--'} mg/dL ·
        Temp ${l.temperature_c ?? '--'} °C · Medicinas: ${l.medication_taken ? '✅' : '❌'}
        ${l.alert_flag && l.alert_message ? `<br>⚠ ${_opsEsc(l.alert_message)}` : ''}
      </div>`).join('') || '<p style="font-size:12px;opacity:0.7;">Sin registros diarios aún.</p>';

    body.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px;">
        <div>
          <h3 style="margin:0;">${_opsEsc(data.nombre_completo)}</h3>
          <small style="opacity:0.75;">Diagnóstico reciente: ${_opsEsc(data.ultimo_diagnostico)}</small>
        </div>
        <a class="btn-outline-pill" style="text-decoration:none;" href="/mi-salud/${encodeURIComponent(data.curp)}" target="_blank">📱 Abrir vista móvil ciudadana ↗</a>
      </div>
      <h4 style="margin:8px 0 6px;">💊 Horario Visual de Medicamentos</h4>
      ${slotsHtml}
      <div class="portal-red-box">
        <strong>🚨 Cuándo acudir a Urgencias de inmediato:</strong>
        <ul style="margin:6px 0 0;padding-left:18px;">${flags}</ul>
      </div>
      <h4 style="margin:10px 0 6px;">📝 Registrar chequeo diario en casa</h4>
      <div class="manual-vitals-grid">
        <label>TA Sistólica<input type="number" id="portal-bp-s" class="input-field" placeholder="122" /></label>
        <label>TA Diastólica<input type="number" id="portal-bp-d" class="input-field" placeholder="80" /></label>
        <label>Glucosa (mg/dL)<input type="number" id="portal-gluc" class="input-field" placeholder="108" /></label>
        <label>Temperatura (°C)<input type="number" step="0.1" id="portal-temp" class="input-field" placeholder="36.5" /></label>
        <label>¿Tomó medicinas?<select id="portal-med-ok" class="input-field"><option value="true">Sí</option><option value="false">No</option></select></label>
        <label>Estado hoy<select id="portal-mood" class="input-field"><option value="Bien">Bien</option><option value="Molestia leve">Molestia leve</option><option value="Síntomas importantes">Síntomas importantes</option></select></label>
      </div>
      <div style="display:flex;gap:8px;margin-top:8px;">
        <input type="text" id="portal-note" class="input-field" placeholder="Síntomas o comentarios del paciente..." style="flex:1;" />
        <button class="btn-red-cta" onclick="submitPatientDailyLog('${_opsEsc(data.curp)}')">Guardar chequeo</button>
      </div>
      <div id="portal-log-msg" style="margin-top:6px;font-size:12px;"></div>
      <h4 style="margin:12px 0 6px;">📊 Últimos registros del paciente</h4>
      ${logs}`;
  } catch (e) {
    body.innerHTML = `<p style="color:#dc2626;">Error cargando portal: ${_opsEsc(e.message)}</p>`;
  }
}

function closePortalModal() {
  document.getElementById('portal-modal-overlay')?.classList.remove('open');
}

async function submitPatientDailyLog(curp) {
  const msg = document.getElementById('portal-log-msg');
  const payload = {
    systolic_bp: parseFloat(document.getElementById('portal-bp-s')?.value) || null,
    diastolic_bp: parseFloat(document.getElementById('portal-bp-d')?.value) || null,
    glucose_mg_dl: parseFloat(document.getElementById('portal-gluc')?.value) || null,
    temperature_c: parseFloat(document.getElementById('portal-temp')?.value) || null,
    medication_taken: document.getElementById('portal-med-ok')?.value === 'true',
    mood_or_pain: document.getElementById('portal-mood')?.value || 'Bien',
    symptoms_note: document.getElementById('portal-note')?.value?.trim() || null,
  };
  try {
    const res = await fetch(`${API}/api/patient-portal/${encodeURIComponent(curp)}/logs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const out = await res.json();
    if (!res.ok) throw new Error(out.detail || 'Error al guardar');
    showToast(out.alert_flag ? `Alerta registrada: ${out.alert_message}` : 'Chequeo diario guardado', out.alert_flag ? 'error' : 'success');
    await openPatientPortalModal(curp);
  } catch (e) {
    if (msg) msg.innerHTML = `<span class="import-warn">${_opsEsc(e.message)}</span>`;
  }
}

/* ── CALCULADORAS CLÍNICAS AMPLIADAS (100% OFFLINE) ── */
function calcSuiteAll() {
  calcSuiteImcPam();
  calcCkdEpi();
  calcQsofa();
  calcGlasgow();
  calcCha2ds2();
  calcSuitePed();
}

function calcSuiteImcPam() {
  const peso = parseFloat(document.getElementById('tool-peso')?.value);
  const talla = parseFloat(document.getElementById('tool-talla')?.value);
  const tas = parseFloat(document.getElementById('tool-tas')?.value);
  const tad = parseFloat(document.getElementById('tool-tad')?.value);
  const out = document.getElementById('tool-imc-pam-out');
  if (!out) return;
  const parts = [];
  if (peso > 0 && talla > 0) {
    const imc = peso / ((talla / 100) ** 2);
    const cat = imc < 18.5 ? 'Bajo peso' : imc < 25 ? 'Normal' : imc < 30 ? 'Sobrepeso' : 'Obesidad';
    parts.push(`<strong>IMC:</strong> ${imc.toFixed(1)} kg/m² (${cat})`);
  }
  if (tas > 0 && tad > 0) {
    const pam = (tas + 2 * tad) / 3;
    const tag = pam < 65 ? '⚠ Hipoperfusión' : pam > 110 ? '⚠ Elevada' : 'Normal';
    parts.push(`<strong>PAM:</strong> ${pam.toFixed(1)} mmHg (${tag})`);
  }
  out.innerHTML = parts.length ? parts.join(' &bull; ') : 'Ingresa peso/talla o presión arterial.';
}

function calcCkdEpi() {
  const cr = parseFloat(document.getElementById('tool-creat')?.value);
  const age = parseFloat(document.getElementById('tool-edad')?.value);
  const sex = document.getElementById('tool-sexo')?.value || 'M';
  const out = document.getElementById('tool-ckd-out');
  if (!out) return;
  if (!(cr > 0 && age > 0)) {
    out.textContent = 'Ingresa creatinina (mg/dL) y edad para estimar TFG (CKD-EPI 2021).';
    return;
  }
  const kappa = sex === 'F' ? 0.7 : 0.9;
  const alpha = sex === 'F' ? -0.241 : -0.302;
  const minR = Math.min(cr / kappa, 1);
  const maxR = Math.max(cr / kappa, 1);
  const sexFactor = sex === 'F' ? 1.012 : 1.0;
  const egfr = 142 * (minR ** alpha) * (maxR ** -1.2) * (0.9938 ** age) * sexFactor;
  const stage = egfr >= 90 ? 'G1 (Normal)' : egfr >= 60 ? 'G2 (Leve)' : egfr >= 45 ? 'G3a (Moderada)' : egfr >= 30 ? 'G3b (Ajustar fármacos)' : egfr >= 15 ? 'G4 (Grave — evitar AINEs/Metformina)' : 'G5 (Falla renal)';
  out.innerHTML = `<strong>TFG:</strong> ${egfr.toFixed(1)} mL/min/1.73m² &bull; <strong>Estadio:</strong> ${stage}`;
}

function calcQsofa() {
  const fr = parseFloat(document.getElementById('tool-qsofa-fr')?.value);
  const tas = parseFloat(document.getElementById('tool-qsofa-tas')?.value);
  const gcsAlt = document.getElementById('tool-qsofa-gcs')?.checked ? 1 : 0;
  const out = document.getElementById('tool-qsofa-out');
  if (!out) return;
  let score = gcsAlt;
  if (fr >= 22) score += 1;
  if (tas > 0 && tas <= 100) score += 1;
  const riesgo = score >= 2 ? '🚨 ALTO RIESGO DE SEPSIS (≥2) — Activar Código Sepsis' : `Bajo (${score}/3)`;
  out.innerHTML = `<strong>qSOFA:</strong> ${score}/3 puntos &bull; ${riesgo}`;
}

function calcGlasgow() {
  const o = parseInt(document.getElementById('tool-gcs-o')?.value || '4', 10);
  const v = parseInt(document.getElementById('tool-gcs-v')?.value || '5', 10);
  const m = parseInt(document.getElementById('tool-gcs-m')?.value || '6', 10);
  const total = o + v + m;
  const out = document.getElementById('tool-gcs-out');
  if (!out) return;
  const sev = total <= 8 ? '🚨 Traumatismo/Deterioro GRAVE (≤8 — valorar vía aérea)' : total <= 12 ? '⚠️ Moderado (9–12)' : 'Leve / Normal (13–15)';
  out.innerHTML = `<strong>Glasgow Total:</strong> ${total}/15 &bull; ${sev}`;
}

function calcCha2ds2() {
  let pts = 0;
  document.querySelectorAll('.cha-chk:checked').forEach(el => {
    pts += parseInt(el.dataset.pts || '1', 10);
  });
  const out = document.getElementById('tool-cha-out');
  if (!out) return;
  const rec = pts === 0 ? 'Riesgo bajo — sin anticoagulación habitual' : pts === 1 ? 'Riesgo moderado — considerar anticoagulante oral' : '🚨 Riesgo alto (≥2) — Anticoagulación oral recomendada';
  out.innerHTML = `<strong>CHA₂DS₂-VASc:</strong> ${pts} pts &bull; ${rec}`;
}

function calcSuitePed() {
  const pPed = parseFloat(document.getElementById('tool-ped-peso')?.value);
  const mgkg = parseFloat(document.getElementById('tool-ped-mgkg')?.value);
  const tomas = Math.max(1, parseInt(document.getElementById('tool-ped-tomas')?.value || '3', 10));
  const out = document.getElementById('tool-ped-out');
  if (!out) return;
  if (pPed > 0 && mgkg > 0) {
    const total = pPed * mgkg;
    out.innerHTML = `<strong>Total/día:</strong> ${total.toFixed(0)} mg &bull; <strong>Por toma:</strong> ${(total / tomas).toFixed(0)} mg c/${Math.round(24 / tomas)} h`;
  } else {
    out.textContent = 'Ingresa peso y dosis mg/kg/día.';
  }
}


// ─────────────────────────────────────────────────────────────────
// SPRINT 4: ROLES (RBAC), CÉDULA PROFESIONAL, OFFLINE & AUDITORÍA NOM-024
// ─────────────────────────────────────────────────────────────────

const _Sprint4State = {
  profiles: [],
  permissionsMatrix: {},
  selectedRole: 'Médico',
  auditLogs: [],
};

async function loadActiveOperatorProfile() {
  try {
    const res = await _getJson(`${API}/api/security/profile`);
    _Sprint4State.profiles = res.profiles || [];
    _Sprint4State.permissionsMatrix = res.permissions_matrix || {};
    if (res.active) {
      AppState.operatorProfile = res.active;
      _Sprint4State.selectedRole = res.active.role || 'Médico';
      _syncOperatorUi();
    }
    return res;
  } catch (e) {
    console.warn('[Security] Error cargando perfil:', e);
    return null;
  }
}

function _syncOperatorUi() {
  const op = AppState.operatorProfile || {};
  const role = op.role || 'Médico';
  const name = op.full_name || 'Dr. Roberto Morales';
  const cedula = op.cedula_profesional || 'Sin cédula';

  const words = name.replace(/^(Dr\.|Dra\.|Enf\.|Lic\.|Dir\.)\s*/i, '').trim().split(/\s+/);
  const initials = words.length >= 2
    ? `${words[0][0] || ''}${words[1][0] || ''}`.toUpperCase()
    : name.slice(0, 2).toUpperCase();

  _setText('sidebar-profile-avatar', initials || 'DR');
  _setText('sidebar-profile-name', name);
  _setText('sidebar-profile-role', `${role} • ${cedula}`);
  _setText('topbar-role-label', `${role} • ${cedula}`);

  const badge = document.getElementById('cfg-active-role-badge');
  if (badge) badge.textContent = `Activo: ${role}`;

  const perms = _Sprint4State.permissionsMatrix[role] || {};
  const btnNueva = document.getElementById('nav-btn-consulta');
  if (btnNueva) {
    const canSign = perms.sign_consultation !== false;
    btnNueva.title = canSign
      ? 'Nueva consulta y nota médica NOM-004'
      : `Modo consulta limitado para ${role} (firma bloqueada por RBAC)`;
  }

  _renderGreeting();
  if (typeof _applyStaffRbacUi === 'function') _applyStaffRbacUi(role, perms);
}

async function loadSecurityConfigView() {
  const data = await loadActiveOperatorProfile();
  if (data) {
    selectConfigRole(AppState.operatorProfile.role || 'Médico');
  }
  loadAuditLogsView();
}

function selectConfigRole(role) {
  _Sprint4State.selectedRole = role;
  document.querySelectorAll('#cfg-role-pills .cfg-role-pill').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.role === role);
  });
  const prof = _Sprint4State.profiles.find(p => p.role === role) || AppState.operatorProfile || {};
  const setVal = (id, v) => { const el = document.getElementById(id); if (el) el.value = v || ''; };
  setVal('cfg-role-name', role);
  setVal('cfg-full-name', prof.full_name || '');
  setVal('cfg-cedula', prof.cedula_profesional || '');
  setVal('cfg-specialty', prof.specialty || '');
  setVal('cfg-clues', prof.clues_institucion || 'YUC-CR-001');
  _renderPermissionsMatrix(role);

  const testOut = document.getElementById('cfg-rbac-test-result');
  if (testOut) testOut.style.display = 'none';
}

function _renderPermissionsMatrix(role) {
  const grid = document.getElementById('cfg-perms-grid');
  if (!grid) return;
  const perms = _Sprint4State.permissionsMatrix[role] || {};
  const labels = [
    ['view_clinical', 'Consultar expedientes'],
    ['register_patient', 'Registrar / editar pacientes'],
    ['manage_appointments', 'Agenda y sala de triaje'],
    ['record_vitals', 'Signos vitales y wearables'],
    ['sign_consultation', 'Firmar notas NOM-004'],
    ['prescribe', 'Emitir recetas médicas'],
    ['add_addendum', 'Agregar addenda inmutables'],
    ['read_audit', 'Bitácora NOM-024'],
  ];
  grid.innerHTML = labels.map(([k, txt]) => {
    const ok = !!perms[k];
    return `<div class="cfg-perm-chip ${ok ? 'perm-allow' : 'perm-deny'}">${ok ? '✅' : '🔒'} ${txt}</div>`;
  }).join('');
}

async function saveSecurityProfile() {
  const payload = {
    role: document.getElementById('cfg-role-name')?.value || _Sprint4State.selectedRole,
    full_name: document.getElementById('cfg-full-name')?.value.trim() || 'Operador',
    cedula_profesional: document.getElementById('cfg-cedula')?.value.trim() || '',
    specialty: document.getElementById('cfg-specialty')?.value.trim() || '',
    clues_institucion: document.getElementById('cfg-clues')?.value.trim() || 'YUC-CR-001',
    activate: true,
  };
  try {
    const res = await fetch(`${API}/api/security/profile`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Error al guardar perfil');
    _Sprint4State.profiles = data.profiles || _Sprint4State.profiles;
    _Sprint4State.permissionsMatrix = data.permissions_matrix || _Sprint4State.permissionsMatrix;
    AppState.operatorProfile = data.active;
    _syncOperatorUi();
    loadAuditLogsView();
    showToast(`Rol activado: ${data.active.role} (${data.active.cedula_profesional || 'sin cédula'})`, 'success');
  } catch (e) {
    showToast(e.message || 'No se pudo actualizar el rol', 'error');
  }
}

async function testCurrentRoleBoundary() {
  const out = document.getElementById('cfg-rbac-test-result');
  const activeRole = AppState.operatorProfile?.role || 'Médico';
  if (out) {
    out.style.display = 'block';
    out.textContent = `Probando autorización RBAC en servidor para "${activeRole}"...`;
  }
  try {
    const res = await fetch(`${API}/api/consultations/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Operator-Role': encodeURIComponent(activeRole),
      },
      body: JSON.stringify({ evento_id: '__rbac_probe__', doctor_nombre: 'Probe' }),
    });
    const body = await res.json().catch(() => ({}));
    if (res.status === 403) {
      if (out) out.innerHTML = `🔒 <strong>RBAC Bloqueado (HTTP 403):</strong> ${_opsEsc(body.detail || 'Acceso denegado para firmar consultas.')}`;
    } else if (res.status === 404) {
      if (out) out.innerHTML = `✅ <strong>RBAC Autorizado (pase clínico validado):</strong> El rol <em>${_opsEsc(activeRole)}</em> tiene permiso de firma NOM-004.`;
    } else {
      if (out) out.innerHTML = `ℹ️ Respuesta HTTP ${res.status}: ${_opsEsc(JSON.stringify(body.detail || body))}`;
    }
  } catch (e) {
    if (out) out.textContent = `Error probando RBAC: ${e.message}`;
  }
}

async function runOfflineDiagnostics() {
  const listEl = document.getElementById('offline-checks-list');
  const badge = document.getElementById('offline-overall-badge');
  if (listEl) listEl.innerHTML = '<div class="wearable-empty">Ejecutando auditoría local (0 llamadas externas)...</div>';
  try {
    const res = await _getJson(`${API}/api/security/offline-readiness`);
    if (badge) {
      badge.textContent = res.offline_capable ? `100% OFFLINE OK (${res.checked_at_ms} ms)` : 'Requiere atención';
      badge.style.background = res.offline_capable ? 'rgba(16,185,129,0.14)' : 'rgba(239,68,68,0.14)';
      badge.style.color = res.offline_capable ? '#059669' : '#dc2626';
    }
    if (listEl) {
      listEl.innerHTML = (res.checks || []).map(c => `
        <div class="offline-check-item ${c.ok ? 'chk-ok' : 'chk-fail'}">
          <span class="chk-icon">${c.ok ? '✅' : '❌'}</span>
          <div>
            <div class="chk-name">${_opsEsc(c.name)}</div>
            <div class="chk-detail">${_opsEsc(c.detail)}</div>
          </div>
        </div>
      `).join('');
    }
    showToast(res.offline_capable ? 'Resiliencia 100% Offline verificada ✅' : 'Algún subsistema requiere revisión', res.offline_capable ? 'success' : 'error');
  } catch (e) {
    if (listEl) listEl.innerHTML = `<div class="wearable-empty">Error verificando subsistemas: ${_opsEsc(e.message)}</div>`;
  }
}

async function loadAuditLogsView() {
  const tbody = document.getElementById('audit-logs-tbody');
  const sumRow = document.getElementById('audit-summary-row');
  const action = document.getElementById('audit-filter-action')?.value || 'ALL';
  const curp = document.getElementById('audit-filter-curp')?.value.trim() || '';
  try {
    const qs = new URLSearchParams({ limit: '80', action });
    if (curp) qs.set('curp', curp);
    const data = await _getJson(`${API}/api/security/audit-logs?${qs.toString()}`);
    const logs = data.logs || [];
    _Sprint4State.auditLogs = logs;

    if (sumRow && data.summary) {
      sumRow.innerHTML = `
        <span class="audit-sum-pill">🗂️ Eventos auditados: <strong>${data.summary.total_audit_events}</strong></span>
        <span class="audit-sum-pill">🔒 Consultas inmutables: <strong>${data.summary.total_consultas_inmutables}</strong></span>
        <span class="audit-sum-pill">👥 Expedientes: <strong>${data.summary.total_pacientes}</strong></span>
      `;
    }

    if (!tbody) return;
    if (!logs.length) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; padding:18px; opacity:0.7;">Sin registros de auditoría para este filtro.</td></tr>';
      return;
    }
    tbody.innerHTML = logs.map(l => {
      const ts = (l.timestamp || '').replace('T', ' ').slice(0, 19);
      const det = Object.entries(l.details || {}).slice(0, 3).map(([k, v]) => `${k}: ${typeof v === 'object' ? JSON.stringify(v) : v}`).join(' • ');
      return `
        <tr>
          <td style="white-space:nowrap; font-family:monospace; font-size:11.5px;">${_opsEsc(ts)}</td>
          <td><span class="audit-action-badge">${_opsEsc(l.action)}</span></td>
          <td style="font-family:monospace; font-size:12px;">${_opsEsc(l.patient_curp)}</td>
          <td>${_opsEsc(l.operator)}</td>
          <td style="font-size:12px; opacity:0.82; max-width:340px; overflow:hidden; text-overflow:ellipsis;">${_opsEsc(det || '—')}</td>
        </tr>
      `;
    }).join('');
  } catch (e) {
    if (tbody) tbody.innerHTML = `<tr><td colspan="5">Error cargando bitácora: ${_opsEsc(e.message)}</td></tr>`;
  }
}

function exportAuditLogsCsv() {
  const logs = _Sprint4State.auditLogs || [];
  if (!logs.length) return showToast('No hay registros en bitácora para exportar', 'error');
  const header = ['timestamp_utc', 'action', 'patient_curp', 'operator', 'details'];
  const esc = v => `"${String(v ?? '').replace(/"/g, '""')}"`;
  const rows = [header.join(',')].concat(
    logs.map(l => [l.timestamp, l.action, l.patient_curp, l.operator, JSON.stringify(l.details || {})].map(esc).join(','))
  );
  const blob = new Blob([rows.join('\n')], { type: 'text/csv;charset=utf-8;' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `Medicaition_Bitacora_NOM024_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}


// =====================================================================
// MARCO LEGAL, CONSENTIMIENTO INFORMADO Y SEGURIDAD (MÉXICO / YUCATÁN)
// =====================================================================
const _LegalState = {
  framework: null,
  securityAudit: null,
  systemConsent: null,
};

async function checkLegalConsentGate() {
  // Solo verifica compromiso de confidencialidad cuando hay sesión de Personal Clínico
  if (!AppState.session || AppState.session.userType !== 'staff') return;
  try {
    const res = await fetch(`${API}/api/auth/roles`);
    if (!res.ok) return;
    const data = await res.json();
    const role = AppState.operatorProfile?.role || AppState.session?.role || 'Médico';
    const match = (data.staff_roles || []).find(r => r.role === role);
    if (match && !match.confidentiality_accepted) {
      openLegalConsentGate();
    }
  } catch (e) {
    console.warn('No se pudo verificar confidencialidad del operador:', e);
  }
}

function openLegalConsentGate() {
  document.getElementById('legal-gate-overlay')?.classList.add('open');
}

function closeLegalConsentGate() {
  document.getElementById('legal-gate-overlay')?.classList.remove('open');
}

async function acceptLegalGateConsent() {
  const secretOk = !!document.getElementById('gate-chk-privacy')?.checked;
  const cdssOk   = !!document.getElementById('gate-chk-responsibility')?.checked;

  if (!secretOk || !cdssOk) {
    return showToast('Debes aceptar el secreto profesional NOM-024 y la responsabilidad clínica CDSS para operar.', 'error');
  }

  const role = AppState.operatorProfile?.role || AppState.session?.role || 'Médico';
  const fullName = AppState.operatorProfile?.full_name || role;

  try {
    const res = await fetch(`${API}/api/auth/staff-confidentiality`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        role,
        full_name: fullName,
        accepted_confidentiality: true,
        accepted_cdss_responsibility: true,
      }),
    });
    if (!res.ok) throw new Error(await res.text());
    closeLegalConsentGate();
    showToast('✅ Compromiso de confidencialidad NOM-024 registrado para ' + role, 'success');
  } catch (err) {
    showToast('Error al registrar compromiso: ' + err.message, 'error');
  }
}

async function loadLegalView() {
  try {
    const [fwRes, auditRes, ptsRes] = await Promise.all([
      fetch(`${API}/api/legal/framework`),
      fetch(`${API}/api/legal/security-audit`),
      fetch(`${API}/api/patients/`),
    ]);

    if (fwRes.ok) {
      const fwData = await fwRes.json();
      _LegalState.framework = fwData.framework || {};
      _LegalState.systemConsent = fwData.system_consent || null;
      _renderLegalFramework(fwData.framework || {}, fwData.system_consent);
    }

    if (auditRes.ok) {
      const auditData = await auditRes.json();
      _LegalState.securityAudit = auditData;
      _renderLegalSecurityAudit(auditData);
    }

    if (ptsRes.ok) {
      const ptsData = await ptsRes.json();
      const patients = Array.isArray(ptsData) ? ptsData : (ptsData.patients || []);
      const sel = document.getElementById('legal-target-select');
      if (sel) {
        const prev = sel.value || 'SYSTEM';
        sel.innerHTML = '<option value="SYSTEM">Operador / Sistema MedicAItion (Aviso General)</option>';
        patients.forEach(p => {
          const fullName = `${p.primer_apellido || ''} ${p.segundo_apellido || ''} ${p.nombres || ''}`.trim() || p.curp;
          const opt = document.createElement('option');
          opt.value = p.curp;
          opt.textContent = `${fullName} (${p.curp})`;
          sel.appendChild(opt);
        });
        if ([...sel.options].some(o => o.value === prev)) sel.value = prev;
      }
    }

    await loadTargetConsent();
  } catch (err) {
    console.error('Error cargando vista Legal:', err);
    showToast('Error cargando módulo legal: ' + err.message, 'error');
  }
}

function _renderLegalSecurityAudit(audit) {
  const titleEl   = document.getElementById('legal-enc-title');
  const subEl     = document.getElementById('legal-enc-sub');
  const metricsEl = document.getElementById('legal-enc-metrics');
  const bannerEl  = document.getElementById('legal-encryption-banner');

  const vault    = audit.vault || {};
  const tampered = audit.consultas_tampered ?? 0;
  const safeOk   = audit.patient_safety_ok !== false && tampered === 0;
  const alg      = vault.cipher_suite || 'ChaCha20 + HMAC-SHA256 (256-bit)';

  if (bannerEl) {
    bannerEl.classList.toggle('alert-danger', !safeOk);
  }
  if (titleEl) {
    titleEl.textContent = safeOk
      ? `Bóveda Activa: ${alg} — Integridad Verificada`
      : `⚠️ Alerta de Integridad NOM-004 (${tampered} registros alterados)`;
  }
  if (subEl) {
    const encPatients = audit.patients_sensitive_encrypted ?? 0;
    const totPatients = audit.patients_with_sensitive ?? audit.patients_total ?? encPatients;
    const encConsults = audit.consultas_encrypted ?? 0;
    const totConsults = audit.consultas_total ?? encConsults;
    const sealedOk    = audit.consultas_seal_verified ?? totConsults;
    const fp          = vault.key_fingerprint ? ` · Huella llave: ${vault.key_fingerprint}` : '';
    subEl.textContent =
      `Expedientes cifrados: ${encPatients}/${totPatients} · Consultas cifradas: ${encConsults}/${totConsults} · Sellos NOM-004 válidos: ${sealedOk}${fp}`;
  }
  if (metricsEl) {
    const activeC = audit.active_consents ?? 0;
    metricsEl.innerHTML = `
      <span class="legal-metric-pill ${safeOk ? 'ok' : 'err'}">${safeOk ? '🔒 Cifrado En Reposo OK' : '⚠️ Revisar Sellos'}</span>
      <span class="legal-metric-pill">${_opsEsc(String(activeC))} Consentimientos</span>
    `;
  }
}

function _renderLegalFramework(fw, sysConsent) {
  const badgeEl   = document.getElementById('legal-consent-status-badge');
  const metaEl    = document.getElementById('legal-jurisdiction-meta');
  const normsEl   = document.getElementById('legal-norms-list');
  const privEl    = document.getElementById('legal-privacy-full-text');
  const discEl    = document.getElementById('legal-clinical-disclaimer-text');

  if (badgeEl) {
    const ok = sysConsent && sysConsent.status === 'active' && sysConsent.accepted_privacy_notice;
    badgeEl.textContent = ok
      ? `✓ Sistema Autorizado (v${fw.version || '1.0'})`
      : '⚠ Consentimiento General Pendiente';
    badgeEl.classList.toggle('signed', !!ok);
  }

  if (metaEl) {
    const jur = fw.jurisdiccion_inicial || {};
    const exp = fw.alcance_expansion || {};
    const jurStr = typeof jur === 'string'
      ? jur
      : `${jur.pais || 'México'} — ${jur.estado_piloto || 'Yucatán (SSY / INAIP)'}${jur.ciudad ? ' (' + jur.ciudad + ')' : ''}`;
    const expStr = typeof exp === 'string'
      ? exp
      : (exp.modelo || exp.descripcion || 'Arquitectura multi-CLUES federal (32 estados) e interoperabilidad HL7 FHIR R4');
    metaEl.innerHTML = `
      <div><strong>Jurisdicción Inicial:</strong> ${_opsEsc(jurStr)}</div>
      <div><strong>Escalabilidad:</strong> ${_opsEsc(expStr)}</div>
    `;
  }

  if (normsEl) {
    const norms = fw.normatividad || [];
    normsEl.innerHTML = norms.length
      ? norms.map(n => `
          <div class="legal-norm-item">
            <div class="legal-norm-code">${_opsEsc(n.codigo || n.code || '')}</div>
            <div>
              <div class="legal-norm-title">${_opsEsc(n.titulo || n.title || '')}</div>
              <div class="legal-norm-desc">${_opsEsc(n.aplicacion || n.description || '')}</div>
            </div>
          </div>
        `).join('')
      : '<p>Sin normas cargadas.</p>';
  }

  if (privEl) {
    privEl.textContent = fw.aviso_privacidad_resumen || fw.privacy_notice || 'Aviso de privacidad LFPDPPP / LGPDPPSO.';
  }
  if (discEl) {
    discEl.textContent = fw.descargo_clinico || fw.clinical_disclaimer || 'Sistema de apoyo clínico CDSS sujeto a criterio del médico titulado.';
  }
}

async function loadTargetConsent() {
  const curp = document.getElementById('legal-target-select')?.value || 'SYSTEM';
  const proofBox = document.getElementById('legal-consent-proof-box');
  try {
    const res = await fetch(`${API}/api/legal/consent/${encodeURIComponent(curp)}`);
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    const c = data.consent;

    document.getElementById('legal-chk-privacy').checked   = c ? !!c.accepted_privacy_notice : true;
    document.getElementById('legal-chk-clinical').checked  = c ? !!c.accepted_clinical_processing : true;
    document.getElementById('legal-chk-local-ai').checked  = c ? !!c.accepted_ai_local_processing : true;
    document.getElementById('legal-chk-cloud-ai').checked  = c ? !!c.accepted_cloud_llm_transfer : false;
    document.getElementById('legal-chk-ice-qr').checked    = c ? !!c.accepted_ice_qr_emergency : true;
    document.getElementById('legal-chk-wearables').checked = c ? !!c.accepted_wearables_monitoring : true;

    const signerInput = document.getElementById('legal-signer-name');
    if (signerInput) signerInput.value = (c && c.signed_by_name) ? c.signed_by_name : '';

    if (proofBox) {
      if (data.has_consent && c) {
        const badge = c.status === 'active' ? '🟢 ACTIVO' : '🟠 REVOCADO PARCIAL (Custodia NOM-004 Activa)';
        proofBox.innerHTML = `
          <strong>Estado:</strong> ${badge} · <strong>Firmante:</strong> ${_opsEsc(c.signed_by_name || 'N/D')} ·
          <strong>Versión:</strong> ${_opsEsc(c.notice_version || '1.0')}<br>
          <strong>Sello SHA-256:</strong> <code>${_opsEsc(c.proof_hash || '—')}</code> ·
          <strong>Fecha UTC:</strong> ${_opsEsc(c.signed_at || c.updated_at || '—')}
        `;
      } else {
        proofBox.textContent = 'Sin firma registrada para este titular todavía. Completa las autorizaciones y presiona "Guardar y Firmar Consentimiento".';
      }
    }
  } catch (err) {
    if (proofBox) proofBox.textContent = 'Error consultando consentimiento: ' + err.message;
  }
}

async function saveTargetConsent() {
  const curp = document.getElementById('legal-target-select')?.value || 'SYSTEM';
  const signer = document.getElementById('legal-signer-name')?.value.trim() || (curp === 'SYSTEM' ? 'Médico Operador' : curp);
  const privacy  = !!document.getElementById('legal-chk-privacy')?.checked;
  const clinical = !!document.getElementById('legal-chk-clinical')?.checked;

  if (!privacy || !clinical) {
    return showToast('El Aviso de Privacidad y el Expediente NOM-004 son obligatorios para operar datos médicos.', 'error');
  }

  try {
    const res = await fetch(`${API}/api/legal/consent/${encodeURIComponent(curp)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        accepted_privacy_notice: privacy,
        accepted_clinical_processing: clinical,
        accepted_ai_local_processing: !!document.getElementById('legal-chk-local-ai')?.checked,
        accepted_cloud_llm_transfer: !!document.getElementById('legal-chk-cloud-ai')?.checked,
        accepted_ice_qr_emergency: !!document.getElementById('legal-chk-ice-qr')?.checked,
        accepted_wearables_monitoring: !!document.getElementById('legal-chk-wearables')?.checked,
        signed_by_name: signer,
        signer_role: curp === 'SYSTEM' ? 'operator' : 'patient_or_representative',
      }),
    });
    if (!res.ok) throw new Error(await res.text());
    showToast('✅ Consentimiento firmado y sellado criptográficamente', 'success');
    await loadLegalView();
  } catch (err) {
    showToast('Error al firmar consentimiento: ' + err.message, 'error');
  }
}

async function exportTargetArco() {
  const curp = document.getElementById('legal-target-select')?.value || 'SYSTEM';
  if (curp === 'SYSTEM') {
    return showToast('Selecciona un paciente del expediente para exportar su paquete ARCO.', 'error');
  }
  try {
    const res = await fetch(`${API}/api/legal/arco/${encodeURIComponent(curp)}/export?download=true`);
    if (!res.ok) throw new Error(await res.text());
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ARCO_${curp}_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('📦 Paquete de Portabilidad ARCO exportado', 'success');
  } catch (err) {
    showToast('Error exportando paquete ARCO: ' + err.message, 'error');
  }
}

async function revokeTargetConsent() {
  const curp = document.getElementById('legal-target-select')?.value || 'SYSTEM';
  if (!confirm(`¿Revocar usos opcionales (IA en Nube, QR/ICE, Telemonitoreo) para ${curp}? El expediente NOM-004 conservará custodia legal mínima de 5 años.`)) {
    return;
  }
  try {
    const res = await fetch(`${API}/api/legal/consent/${encodeURIComponent(curp)}/revoke`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        revoke_cloud_llm: true,
        revoke_ice_qr: true,
        revoke_wearables: true,
        reason: 'Revocación de consentimiento (Derechos ARCO / LFPDPPP Art. 8°)',
      }),
    });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    showToast(data.nom004_custody_lock ? '🔒 Usos opcionales revocados (custodia NOM-004 preservada)' : 'Consentimiento revocado', 'info');
    await loadLegalView();
  } catch (err) {
    showToast('Error al revocar consentimiento: ' + err.message, 'error');
  }
}


// =====================================================================
// LOGIN POR ROLES Y SEPARACIÓN ESTRICTA: PERSONAL CLÍNICO VS. PACIENTE
// =====================================================================

function _persistSession(sess) {
  AppState.session = sess;
  try {
    sessionStorage.setItem('medicaition_session_v1', JSON.stringify(sess));
  } catch (_) {}
}

function openAuthLoginModal() {
  document.getElementById('main-app-shell')?.style.setProperty('display', 'none');
  document.getElementById('patient-standalone-view')?.style.setProperty('display', 'none');
  const errEl = document.getElementById('auth-login-error');
  if (errEl) errEl.style.display = 'none';
  document.getElementById('auth-login-overlay')?.classList.add('open');
}

function closeAuthLoginModal() {
  document.getElementById('auth-login-overlay')?.classList.remove('open');
}

function switchAuthLoginTab(mode) {
  const isPatient = mode === 'patient';
  document.getElementById('auth-tab-staff')?.classList.toggle('active', !isPatient);
  document.getElementById('auth-tab-patient')?.classList.toggle('active', isPatient);
  const pStaff = document.getElementById('auth-panel-staff');
  const pPat = document.getElementById('auth-panel-patient');
  if (pStaff) pStaff.style.display = isPatient ? 'none' : 'flex';
  if (pPat) pPat.style.display = isPatient ? 'flex' : 'none';
  const errEl = document.getElementById('auth-login-error');
  if (errEl) errEl.style.display = 'none';
}

function initAuthGateOnStartup() {
  const sess = AppState.session;
  if (sess && sess.authenticated && sess.token) {
    if (sess.userType === 'patient' && sess.patientCurp) {
      _enterPatientStandaloneWorkspace(sess);
      return;
    }
    if (sess.userType === 'staff') {
      _enterStaffWorkspace(sess);
      return;
    }
  }
  openAuthLoginModal();
}

async function submitStaffLogin() {
  const role = document.getElementById('login-staff-role')?.value || 'Médico';
  const pin = document.getElementById('login-staff-pin')?.value?.trim() || '';
  const errEl = document.getElementById('auth-login-error');
  if (errEl) errEl.style.display = 'none';

  try {
    const res = await fetch(`${API}/api/auth/staff-login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role, pin }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || 'Credenciales inválidas');

    const sess = {
      authenticated: true,
      userType: 'staff',
      token: data.token,
      role: data.profile?.role || role,
      permissions: data.permissions || {},
      requiresConfidentialityAck: !!data.requires_confidentiality_ack,
    };
    AppState.operatorProfile = data.profile || AppState.operatorProfile;
    _persistSession(sess);
    closeAuthLoginModal();
    await _enterStaffWorkspace(sess);
    showToast(`Bienvenido, ${AppState.operatorProfile.full_name} (${sess.role})`, 'success');
  } catch (err) {
    if (errEl) {
      errEl.textContent = err.message || 'Error al iniciar sesión';
      errEl.style.display = 'block';
    }
  }
}

async function submitPatientLogin() {
  const curp = (document.getElementById('login-patient-curp')?.value || '').trim().toUpperCase();
  const verification_secret = (document.getElementById('login-patient-secret')?.value || '').trim();
  const errEl = document.getElementById('auth-login-error');
  if (errEl) errEl.style.display = 'none';

  try {
    const res = await fetch(`${API}/api/auth/patient-login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ curp, verification_secret }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || 'CURP o fecha/folio incorrecto');

    const sess = {
      authenticated: true,
      userType: 'patient',
      token: data.token,
      role: 'Paciente',
      patientCurp: data.patient?.curp || curp,
      patientName: data.patient?.nombre_completo || curp,
      permissions: data.permissions || {},
    };
    _persistSession(sess);
    closeAuthLoginModal();
    await _enterPatientStandaloneWorkspace(sess);
    showToast(`Bienvenido a Mi Salud Hoy, ${data.patient?.nombre_corto || curp}`, 'success');
  } catch (err) {
    if (errEl) {
      errEl.textContent = err.message || 'No se pudo iniciar sesión';
      errEl.style.display = 'block';
    }
  }
}

function logoutActiveUser() {
  try { sessionStorage.removeItem('medicaition_session_v1'); } catch (_) {}
  AppState.session = {
    authenticated: false,
    userType: null,
    token: null,
    role: null,
    patientCurp: null,
    patientName: null,
    permissions: {},
  };
  document.body.classList.remove('mode-patient-portal');
  closeLegalConsentGate();
  openAuthLoginModal();
}

async function _enterStaffWorkspace(sess) {
  document.body.classList.remove('mode-patient-portal');
  document.getElementById('patient-standalone-view')?.style.setProperty('display', 'none');
  document.getElementById('main-app-shell')?.style.removeProperty('display');

  if (typeof loadActiveOperatorProfile === 'function') await loadActiveOperatorProfile();
  _applyStaffRbacUi(sess.role || AppState.operatorProfile?.role, sess.permissions);

  const perms = sess.permissions || _Sprint4State.permissionsMatrix[sess.role] || {};
  if (perms.view_clinical !== false) {
    if (typeof loadPatients === 'function') loadPatients();
    if (typeof refreshDashboard === 'function') refreshDashboard();
  } else {
    // Recepción: iniciar directo en Agenda/Pacientes sin vistas clínicas
    if (typeof loadPatients === 'function') loadPatients();
    if (typeof switchMainTab === 'function') switchMainTab('agenda');
  }
  if (typeof loadAppointments === 'function') loadAppointments();
  if (sess.requiresConfidentialityAck) {
    openLegalConsentGate();
  } else {
    checkLegalConsentGate();
  }
}

function _applyStaffRbacUi(role, permsOverride) {
  const r = role || AppState.operatorProfile?.role || 'Médico';
  const perms = (permsOverride && Object.keys(permsOverride).length ? permsOverride : null)
    || _Sprint4State.permissionsMatrix[r]
    || {};

  const setShow = (id, show) => {
    const el = document.getElementById(id);
    if (el) el.style.display = show ? '' : 'none';
  };

  setShow('nav-btn-consulta', perms.sign_consultation !== false || perms.record_vitals === true);
  setShow('nav-btn-ia-tools', perms.view_clinical !== false);
  setShow('nav-btn-reportes', perms.view_clinical !== false);
  setShow('nav-btn-config', perms.manage_config !== false);
  setShow('nav-btn-wearables', perms.record_vitals !== false || perms.view_clinical !== false);
  // Legal está visible para que Médico/Recepción recaben consentimiento y Admin audite
  setShow('nav-btn-legal', true);

  if (r === 'Recepción') {
    setShow('nav-btn-dashboard', false);
    setShow('nav-btn-consulta', false);
    setShow('nav-btn-clinica-exp', false);
  } else {
    setShow('nav-btn-dashboard', true);
    setShow('nav-btn-clinica-exp', true);
  }
}

async function updateSelectedRolePin() {
  const role = document.getElementById('cfg-role-name')?.value || _Sprint4State.selectedRole || 'Médico';
  const current_pin = document.getElementById('cfg-pin-current')?.value?.trim() || '';
  const new_pin = document.getElementById('cfg-pin-new')?.value?.trim() || '';
  if (!current_pin || new_pin.length < 4) {
    return showToast('Ingresa el PIN actual y un nuevo PIN de al menos 4 dígitos.', 'error');
  }
  try {
    const res = await fetch(`${API}/api/auth/staff-pin`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ role, current_pin, new_pin }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || 'No se pudo actualizar el PIN');
    document.getElementById('cfg-pin-current').value = '';
    document.getElementById('cfg-pin-new').value = '';
    showToast(`🔐 PIN actualizado para el rol ${role}`, 'success');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

// ── PORTAL EXCLUSIVO DEL PACIENTE (AISLADO DEL ENTORNO MÉDICO) ──
async function _enterPatientStandaloneWorkspace(sess) {
  document.body.classList.add('mode-patient-portal');
  document.getElementById('main-app-shell')?.style.setProperty('display', 'none');
  document.getElementById('patient-standalone-view')?.style.setProperty('display', 'block');
  closeLegalConsentGate();
  await loadStandalonePatientPortal(sess.patientCurp);
}

async function loadStandalonePatientPortal(curpOverride) {
  const curp = (curpOverride || AppState.session?.patientCurp || '').toUpperCase();
  if (!curp) return;

  try {
    const res = await fetch(`${API}/api/patient-portal/${encodeURIComponent(curp)}`);
    if (res.status === 401 || res.status === 403) {
      logoutActiveUser();
      return;
    }
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();

    _setText('pat-welcome-name', `Hola, ${data.nombre_completo || curp}`);
    _setText(
      'pat-welcome-meta',
      `CURP: ${curp} · Tipo de sangre: ${data.tipo_sangre || 'No especificado'} · Tu sesión está aislada y cifrada`
    );

    // 1. Medicinas de hoy en formato simple
    const medsEl = document.getElementById('pat-portal-meds');
    if (medsEl) {
      let slotsHtml = '';
      for (const [slot, items] of Object.entries(data.horario_visual || {})) {
        if (!items.length) continue;
        slotsHtml += `
          <div class="portal-slot-box" style="margin-bottom:8px;">
            <h5 style="margin:0 0 4px;">${_opsEsc(slot)}</h5>
            <ul style="margin:0; padding-left:18px; font-size:13px;">
              ${items.map(m => `<li><strong>${_opsEsc(m.nombre)}</strong> — ${_opsEsc(m.dosis)} (${_opsEsc(m.duracion || 'según indicación')})</li>`).join('')}
            </ul>
          </div>`;
      }
      medsEl.innerHTML = (slotsHtml || '<p style="font-size:13px; color:#64748b;">No tienes medicamentos activos registrados en este momento.</p>') +
        `<div style="margin-top:8px; font-size:12.5px; color:#475569;"><strong>Indicaciones:</strong> ${_opsEsc(data.receta_amigable || '')}</div>`;
    }

    // 2. Banderas rojas
    const flagsEl = document.getElementById('pat-portal-redflags');
    if (flagsEl) {
      flagsEl.innerHTML = `<ul style="margin:0; padding-left:18px; font-size:13px; color:#b91c1c;">
        ${(data.banderas_rojas || []).map(f => `<li style="margin-bottom:4px;">${_opsEsc(f)}</li>`).join('')}
      </ul>`;
    }

    // 3. Próximas citas
    const apptsEl = document.getElementById('pat-portal-appointments');
    if (apptsEl) {
      const citas = data.citas_proximas || [];
      apptsEl.innerHTML = citas.length
        ? citas.map(c => `
            <div style="padding:8px 10px; border-radius:10px; border:1px solid rgba(148,163,184,0.25); margin-bottom:8px; font-size:12.5px;">
              <strong>📅 ${_opsEsc(c.date)} · ${_opsEsc(c.time)}</strong> — ${_opsEsc(c.reason)}<br/>
              <span style="color:#64748b;">Con ${_opsEsc(c.doctor)} · Estado: ${_opsEsc(c.status)}</span>
            </div>`).join('')
        : '<p style="font-size:13px; color:#64748b;">No tienes citas próximas registradas.</p>';
    }

    // 4. Últimos chequeos
    const logsEl = document.getElementById('pat-portal-logs');
    if (logsEl) {
      const logs = (data.daily_logs || []).slice(0, 5);
      logsEl.innerHTML = logs.length
        ? logs.map(l => `
            <div class="portal-log-row ${l.alert_flag ? 'is-alert' : ''}" style="margin-bottom:6px;">
              <strong>${_opsEsc((l.recorded_at || '').slice(0, 16).replace('T', ' '))}</strong> —
              Presión ${l.systolic_bp ?? '--'}/${l.diastolic_bp ?? '--'} · Glucosa ${l.glucose_mg_dl ?? '--'} ·
              Temp ${l.temperature_c ?? '--'} °C · Medicinas: ${l.medication_taken ? '✅' : '❌'}
              ${l.alert_flag && l.alert_message ? `<br/>⚠️ ${_opsEsc(l.alert_message)}` : ''}
            </div>`).join('')
        : '<p style="color:#64748b;">Aún no has guardado chequeos en casa.</p>';
    }

    // 5. Consentimiento propio LFPDPPP
    const c = data.consentimiento;
    const hasPrivacy = !!(c && c.status === 'active' && c.accepted_privacy_notice);
    const banner = document.getElementById('pat-privacy-alert-banner');
    if (banner) banner.style.display = hasPrivacy ? 'none' : 'flex';

    document.getElementById('pat-priv-privacy').checked   = c ? !!c.accepted_privacy_notice : true;
    document.getElementById('pat-priv-clinical').checked  = c ? !!c.accepted_clinical_processing : true;
    document.getElementById('pat-priv-ice').checked       = c ? !!c.accepted_ice_qr_emergency : true;
    document.getElementById('pat-priv-wearables').checked = c ? !!c.accepted_wearables_monitoring : true;
    document.getElementById('pat-priv-cloud').checked     = c ? !!c.accepted_cloud_llm_transfer : false;

    const proofEl = document.getElementById('pat-priv-proof');
    if (proofEl) {
      proofEl.innerHTML = c
        ? `<strong>Estado:</strong> ${c.status === 'active' ? '🟢 Permisos Activos' : '🟠 Usos Opcionales Revocados (Custodia NOM-004)'} · <strong>Sello SHA-256:</strong> <code>${_opsEsc(c.proof_hash || '—')}</code>`
        : 'Aún no has confirmado tu Aviso de Privacidad. Revisa las opciones de arriba y presiona "Guardar mis Permisos".';
    }
  } catch (err) {
    showToast('Error cargando tu portal: ' + err.message, 'error');
  }
}

async function submitStandaloneDailyLog() {
  const curp = AppState.session?.patientCurp;
  if (!curp) return;
  const payload = {
    systolic_bp: parseFloat(document.getElementById('pat-chk-bp-s')?.value) || null,
    diastolic_bp: parseFloat(document.getElementById('pat-chk-bp-d')?.value) || null,
    glucose_mg_dl: parseFloat(document.getElementById('pat-chk-gluc')?.value) || null,
    temperature_c: parseFloat(document.getElementById('pat-chk-temp')?.value) || null,
    medication_taken: document.getElementById('pat-chk-med-ok')?.value === 'true',
    mood_or_pain: document.getElementById('pat-chk-mood')?.value || 'Bien',
    symptoms_note: document.getElementById('pat-chk-note')?.value?.trim() || null,
  };
  try {
    const res = await fetch(`${API}/api/patient-portal/${encodeURIComponent(curp)}/logs`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const out = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(out.detail || 'Error al guardar chequeo');
    document.getElementById('pat-chk-note').value = '';
    showToast(out.alert_flag ? `⚠️ Guardado con alerta: ${out.alert_message}` : '✅ Tu chequeo de hoy fue guardado', out.alert_flag ? 'error' : 'success');
    await loadStandalonePatientPortal(curp);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function saveStandalonePatientConsent() {
  const curp = AppState.session?.patientCurp;
  if (!curp) return;
  const privacy = !!document.getElementById('pat-priv-privacy')?.checked;
  const clinical = !!document.getElementById('pat-priv-clinical')?.checked;
  if (!privacy || !clinical) {
    return showToast('El Aviso de Privacidad y el expediente clínico NOM-004 son necesarios para tu atención.', 'error');
  }
  try {
    const res = await fetch(`${API}/api/legal/consent/${encodeURIComponent(curp)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        accepted_privacy_notice: privacy,
        accepted_clinical_processing: clinical,
        accepted_ai_local_processing: true,
        accepted_ice_qr_emergency: !!document.getElementById('pat-priv-ice')?.checked,
        accepted_wearables_monitoring: !!document.getElementById('pat-priv-wearables')?.checked,
        accepted_cloud_llm_transfer: !!document.getElementById('pat-priv-cloud')?.checked,
        signed_by_name: AppState.session?.patientName || curp,
        signer_role: 'patient',
      }),
    });
    if (!res.ok) throw new Error(await res.text());
    showToast('✅ Tus permisos LFPDPPP han sido guardados y sellados', 'success');
    await loadStandalonePatientPortal(curp);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function downloadStandaloneArco() {
  const curp = AppState.session?.patientCurp;
  if (!curp) return;
  try {
    const res = await fetch(`${API}/api/legal/arco/${encodeURIComponent(curp)}/export?download=true`);
    if (!res.ok) throw new Error(await res.text());
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Mi_Expediente_ARCO_${curp}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('📦 Tu expediente ARCO fue descargado', 'success');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

async function revokeStandaloneOptionalConsent() {
  const curp = AppState.session?.patientCurp;
  if (!curp) return;
  if (!confirm('¿Desactivar tu QR de emergencias y envío opcional a nube? Tus consultas previas seguirán resguardadas bajo NOM-004 por seguridad clínica.')) {
    return;
  }
  try {
    const res = await fetch(`${API}/api/legal/consent/${encodeURIComponent(curp)}/revoke`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        revoke_ice_qr: true,
        revoke_cloud_llm: true,
        revoke_wearables: false,
        reason: 'Decisión del titular desde Portal Paciente',
      }),
    });
    if (!res.ok) throw new Error(await res.text());
    showToast('🔒 Permisos opcionales revocados', 'info');
    await loadStandalonePatientPortal(curp);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function openStandaloneIcePassport() {
  const curp = AppState.session?.patientCurp;
  if (!curp) return;
  if (typeof openIcePassportModal === 'function') {
    openIcePassportModal(curp);
  } else {
    window.open(`/ice/${encodeURIComponent(curp)}`, '_blank');
  }
}
