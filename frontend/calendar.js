/**
 * calendar.js — MedicAItion v5.1
 * ==========================================================
 * Módulo de Agenda Médica y Calendario Anual (12 Meses) + Vista Mensual.
 * Permite visualizar citas programadas de todo el año, inspeccionar
 * cada día, iniciar consultas desde una cita o agendar nuevas citas.
 */

const MONTHS_ES = [
  'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
  'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
];

const WEEKDAYS_SHORT_ES = ['L', 'M', 'X', 'J', 'V', 'S', 'D'];
const WEEKDAYS_FULL_ES = [
  'Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'
];

function _toLocalDateStr(dateObj) {
  const y = dateObj.getFullYear();
  const m = String(dateObj.getMonth() + 1).padStart(2, '0');
  const d = String(dateObj.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

function _getTodayStr() {
  return _toLocalDateStr(new Date());
}

const CalendarState = {
  year: new Date().getFullYear(),
  month: new Date().getMonth(), // 0-11 (used in 'month' view)
  viewMode: 'year',             // 'year' | 'month'
  selectedDateStr: _getTodayStr(),
  appointments: []
};

window.CalendarState = CalendarState;

function _buildDefaultAppointments() {
  const today = new Date();
  const todayStr = _toLocalDateStr(today);

  const plusDays = (days) => {
    const d = new Date(today);
    d.setDate(d.getDate() + days);
    return _toLocalDateStr(d);
  };

  const y = today.getFullYear();

  return [
    {
      id: 'appt-1',
      date: todayStr,
      time: '09:00',
      patientName: 'Carlos Manuel G.',
      curp: 'GOPC790814HYNCLN04',
      reason: 'Consulta de seguimiento',
      wearable: true,
      wearableText: 'Garmin Active • ❤️ 72 lpm',
      status: 'confirmada'
    },
    {
      id: 'appt-2',
      date: todayStr,
      time: '09:45',
      patientName: 'Kevin Enrique M.',
      curp: 'MOBK070228HYNRTVA3',
      reason: 'Dolor abdominal',
      wearable: true,
      wearableText: 'Apple Watch S9 • Wearable conectado',
      status: 'confirmada'
    },
    {
      id: 'appt-3',
      date: todayStr,
      time: '10:30',
      patientName: 'Juan Pérez G.',
      curp: 'TESTCURP1234567890',
      reason: 'Control general',
      wearable: false,
      wearableText: '',
      status: 'pendiente'
    },
    {
      id: 'appt-4',
      date: plusDays(3),
      time: '11:15',
      patientName: 'Carlos Manuel G.',
      curp: 'GOPC790814HYNCLN04',
      reason: 'Revisión de laboratorios (HbA1c y Lípidos)',
      wearable: true,
      wearableText: 'Garmin Active conectado',
      status: 'programada'
    },
    {
      id: 'appt-5',
      date: `${y}-03-18`,
      time: '10:00',
      patientName: 'Juan Pérez G.',
      curp: 'TESTCURP1234567890',
      reason: 'Control hipertensión trimestral',
      wearable: false,
      wearableText: '',
      status: 'programada'
    },
    {
      id: 'appt-6',
      date: `${y}-06-12`,
      time: '12:30',
      patientName: 'Kevin Enrique M.',
      curp: 'MOBK070228HYNRTVA3',
      reason: 'Valoración preventiva semestral',
      wearable: true,
      wearableText: 'Wearable conectado',
      status: 'programada'
    },
    {
      id: 'appt-7',
      date: `${y}-12-04`,
      time: '09:30',
      patientName: 'Carlos Manuel G.',
      curp: 'GOPC790814HYNCLN04',
      reason: 'Cierre anual y actualización expediente NOM-004',
      wearable: true,
      wearableText: 'Garmin Active conectado',
      status: 'programada'
    }
  ];
}

const APPT_CACHE_KEY = 'medicaition-appointments-cache-v2';
const APPT_STATUS_OPTIONS = ['Programada', 'En Sala / Triaje', 'En Consulta', 'Atendida', 'No asistió'];
const APPT_TRIAGE_OPTIONS = ['ROJO', 'NARANJA', 'AMARILLO', 'VERDE'];

/**
 * Carga las citas desde la API (SQLite). Si el servidor no responde,
 * usa la caché local como respaldo offline (solo lectura).
 */
async function loadAppointments() {
  try {
    const res = await fetch(`${API}/api/appointments/`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    CalendarState.appointments = Array.isArray(data) ? data : [];
    CalendarState._loaded = true;
    CalendarState._offline = false;
    try { localStorage.setItem(APPT_CACHE_KEY, JSON.stringify(CalendarState.appointments)); } catch { /* ignore */ }
  } catch (e) {
    console.warn('Agenda: usando caché offline', e);
    try {
      const raw = localStorage.getItem(APPT_CACHE_KEY);
      CalendarState.appointments = raw ? JSON.parse(raw) : _buildDefaultAppointments();
    } catch {
      CalendarState.appointments = _buildDefaultAppointments();
    }
    CalendarState._loaded = true;
    CalendarState._offline = true;
  }
  updateAgendaBadgeCount();
  if (typeof refreshDashboardAgenda === 'function') refreshDashboardAgenda();
  return CalendarState.appointments;
}

function saveAppointmentsToStorage() {
  try { localStorage.setItem(APPT_CACHE_KEY, JSON.stringify(CalendarState.appointments)); } catch { /* ignore */ }
  updateAgendaBadgeCount();
}

function updateAgendaBadgeCount() {
  const todayStr = _getTodayStr();
  const pendingToday = CalendarState.appointments.filter(a =>
    a.date === todayStr && !['Atendida', 'No asistió'].includes(a.status)
  ).length;
  const badge = document.getElementById('agenda-nav-badge');
  if (badge) {
    badge.textContent = pendingToday;
    badge.style.display = pendingToday > 0 ? '' : 'none';
  }
}

async function updateAppointmentField(apptId, patch) {
  try {
    const res = await fetch(`${API}/api/appointments/${encodeURIComponent(apptId)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'No se pudo actualizar la cita');
    }
    const updated = await res.json();
    const idx = CalendarState.appointments.findIndex(a => a.id === apptId);
    if (idx >= 0) CalendarState.appointments[idx] = updated;
    saveAppointmentsToStorage();
    renderCalendar();
    if (typeof refreshDashboardAgenda === 'function') refreshDashboardAgenda();
    if (typeof refreshDashboardTasks === 'function') refreshDashboardTasks();
    return updated;
  } catch (e) {
    showToast(e.message, 'error');
    return null;
  }
}

function _getAppointmentsByDate(dateStr) {
  return CalendarState.appointments
    .filter(a => a.date === dateStr)
    .sort((a, b) => (a.time || '').localeCompare(b.time || ''));
}

function _formatTime12h(time24) {
  if (!time24 || !time24.includes(':')) return time24 || '';
  const [hStr, mStr] = time24.split(':');
  let h = parseInt(hStr, 10);
  const ampm = h >= 12 ? 'PM' : 'AM';
  h = h % 12 || 12;
  return `${String(h).padStart(2, '0')}:${mStr} ${ampm}`;
}

function _formatDateTitleES(dateStr) {
  const [y, m, d] = dateStr.split('-').map(Number);
  const dt = new Date(y, m - 1, d);
  const weekday = WEEKDAYS_FULL_ES[dt.getDay()];
  const monthName = MONTHS_ES[m - 1];
  const isToday = dateStr === _getTodayStr();
  return `${weekday}, ${d} de ${monthName} de ${y}${isToday ? ' (Hoy)' : ''}`;
}

function setCalendarViewMode(mode) {
  CalendarState.viewMode = mode;
  document.getElementById('cal-btn-year')?.classList.toggle('active', mode === 'year');
  document.getElementById('cal-btn-month')?.classList.toggle('active', mode === 'month');
  renderCalendar();
}

function changeCalendarYear(delta) {
  CalendarState.year += delta;
  renderCalendar();
}

function changeCalendarMonth(delta) {
  CalendarState.month += delta;
  if (CalendarState.month < 0) {
    CalendarState.month = 11;
    CalendarState.year -= 1;
  } else if (CalendarState.month > 11) {
    CalendarState.month = 0;
    CalendarState.year += 1;
  }
  renderCalendar();
}

function jumpToCalendarToday() {
  const now = new Date();
  CalendarState.year = now.getFullYear();
  CalendarState.month = now.getMonth();
  CalendarState.selectedDateStr = _toLocalDateStr(now);
  renderCalendar();
}

function selectCalendarDay(dateStr) {
  CalendarState.selectedDateStr = dateStr;
  const [y, m] = dateStr.split('-').map(Number);
  CalendarState.year = y;
  CalendarState.month = m - 1;
  renderCalendar();
}

function zoomIntoMonth(monthIndex) {
  CalendarState.month = monthIndex;
  setCalendarViewMode('month');
}

function renderCalendar() {
  if (!CalendarState._loaded) {
    loadAppointments().then(() => renderCalendar());
    return;
  }

  const yearDisplay = document.getElementById('cal-year-display');
  if (yearDisplay) yearDisplay.textContent = CalendarState.year;

  const yearTotal = CalendarState.appointments.filter(a => a.date && a.date.startsWith(`${CalendarState.year}-`)).length;
  const summaryEl = document.getElementById('cal-year-total-summary');
  if (summaryEl) {
    summaryEl.innerHTML = `<strong>${yearTotal}</strong> cita${yearTotal === 1 ? '' : 's'} programada${yearTotal === 1 ? '' : 's'} en <strong>${CalendarState.year}</strong>`;
  }

  const container = document.getElementById('calendar-grid-container');
  if (!container) return;

  if (CalendarState.viewMode === 'year') {
    container.innerHTML = _renderFullYearHtml(CalendarState.year);
  } else {
    container.innerHTML = _renderSingleMonthHtml(CalendarState.year, CalendarState.month);
  }

  renderDayInspector();
}

function _renderFullYearHtml(year) {
  const todayStr = _getTodayStr();
  let html = '<div class="cal-year-grid">';

  for (let m = 0; m < 12; m++) {
    const monthPrefix = `${year}-${String(m + 1).padStart(2, '0')}-`;
    const monthAppts = CalendarState.appointments.filter(a => a.date && a.date.startsWith(monthPrefix));
    const firstDay = new Date(year, m, 1);
    // Monday = 0 ... Sunday = 6
    let startOffset = (firstDay.getDay() + 6) % 7;
    const daysInMonth = new Date(year, m + 1, 0).getDate();

    html += `
      <div class="cal-month-card">
        <div class="cal-month-card-header" onclick="zoomIntoMonth(${m})" title="Ampliar vista mensual de ${MONTHS_ES[m]}">
          <span class="cal-month-name">${MONTHS_ES[m]}</span>
          ${monthAppts.length > 0
            ? `<span class="cal-month-count-badge">${monthAppts.length} cita${monthAppts.length > 1 ? 's' : ''}</span>`
            : `<span class="cal-month-zoom-hint">Ver mes &rsaquo;</span>`}
        </div>
        <div class="cal-weekdays-row">
          ${WEEKDAYS_SHORT_ES.map(w => `<span>${w}</span>`).join('')}
        </div>
        <div class="cal-days-grid">
    `;

    for (let empty = 0; empty < startOffset; empty++) {
      html += `<span class="cal-day-cell empty"></span>`;
    }

    for (let d = 1; d <= daysInMonth; d++) {
      const dateStr = `${year}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      const dayAppts = monthAppts.filter(a => a.date === dateStr);
      const isToday = dateStr === todayStr;
      const isSelected = dateStr === CalendarState.selectedDateStr;
      const hasCitas = dayAppts.length > 0;

      const classes = ['cal-day-cell'];
      if (isToday) classes.push('is-today');
      if (isSelected) classes.push('is-selected');
      if (hasCitas) classes.push('has-citas');

      const tooltip = hasCitas
        ? `${dayAppts.length} cita(s): ${dayAppts.map(a => `${_formatTime12h(a.time)} ${a.patientName}`).join(', ')}`
        : `${d} de ${MONTHS_ES[m]} de ${year}`;

      html += `
        <button type="button" class="${classes.join(' ')}" onclick="selectCalendarDay('${dateStr}')" title="${_escCal(tooltip)}">
          <span>${d}</span>
          ${hasCitas ? '<i class="cal-day-dot"></i>' : ''}
        </button>
      `;
    }

    html += `
        </div>
      </div>
    `;
  }

  html += '</div>';
  return html;
}

function _renderSingleMonthHtml(year, month) {
  const todayStr = _getTodayStr();
  const monthPrefix = `${year}-${String(month + 1).padStart(2, '0')}-`;
  const monthAppts = CalendarState.appointments.filter(a => a.date && a.date.startsWith(monthPrefix));
  const firstDay = new Date(year, month, 1);
  let startOffset = (firstDay.getDay() + 6) % 7;
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  let html = `
    <div class="cal-single-month-wrapper">
      <div class="cal-single-month-header">
        <button class="cal-nav-arrow" onclick="changeCalendarMonth(-1)" title="Mes anterior">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="15 18 9 12 15 6"/></svg>
        </button>
        <h3>${MONTHS_ES[month]} ${year}</h3>
        <button class="cal-nav-arrow" onclick="changeCalendarMonth(1)" title="Mes siguiente">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="9 18 15 12 9 6"/></svg>
        </button>
      </div>
      <div class="cal-single-weekdays">
        <span>Lunes</span><span>Martes</span><span>Miércoles</span><span>Jueves</span><span>Viernes</span><span>Sábado</span><span>Domingo</span>
      </div>
      <div class="cal-single-days-grid">
  `;

  for (let empty = 0; empty < startOffset; empty++) {
    html += `<div class="cal-single-cell empty"></div>`;
  }

  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    const dayAppts = monthAppts
      .filter(a => a.date === dateStr)
      .sort((a, b) => (a.time || '').localeCompare(b.time || ''));
    const isToday = dateStr === todayStr;
    const isSelected = dateStr === CalendarState.selectedDateStr;

    const classes = ['cal-single-cell'];
    if (isToday) classes.push('is-today');
    if (isSelected) classes.push('is-selected');

    html += `
      <div class="${classes.join(' ')}" onclick="selectCalendarDay('${dateStr}')">
        <div class="cal-single-cell-top">
          <span class="cal-single-day-num">${d}</span>
          ${dayAppts.length > 0 ? `<span class="cal-single-count">${dayAppts.length}</span>` : ''}
        </div>
        <div class="cal-single-events">
          ${dayAppts.slice(0, 3).map(a => `
            <div class="cal-single-event-chip">
              <strong>${_formatTime12h(a.time).replace(' AM', 'a').replace(' PM', 'p')}</strong> ${_escCal(a.patientName)}
            </div>
          `).join('')}
          ${dayAppts.length > 3 ? `<div class="cal-single-more">+${dayAppts.length - 3} más</div>` : ''}
        </div>
      </div>
    `;
  }

  html += `
      </div>
    </div>
  `;
  return html;
}

function renderDayInspector() {
  const dateStr = CalendarState.selectedDateStr;
  const titleEl = document.getElementById('inspector-date-title');
  const badgeEl = document.getElementById('inspector-day-badge');
  const listEl = document.getElementById('inspector-citas-list');

  if (titleEl) titleEl.textContent = _formatDateTitleES(dateStr);
  const appts = _getAppointmentsByDate(dateStr);

  if (badgeEl) {
    badgeEl.textContent = appts.length > 0
      ? `${appts.length} CITA${appts.length > 1 ? 'S' : ''} PROGRAMADA${appts.length > 1 ? 'S' : ''}`
      : 'SIN CITAS PROGRAMADAS';
  }

  if (!listEl) return;

  if (appts.length === 0) {
    listEl.innerHTML = `
      <div class="inspector-empty">
        <div class="inspector-empty-icon">
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/></svg>
        </div>
        <h4>Día libre en agenda</h4>
        <p>No hay consultas agendadas para esta fecha.</p>
        <button class="btn-dark-pill" onclick="openAppointmentModal('${dateStr}')">+ Agendar Cita este día</button>
      </div>
    `;
    return;
  }

  listEl.innerHTML = appts.map(a => {
    const tri = (a.triage || 'VERDE').toUpperCase();
    const done = ['Atendida', 'No asistió'].includes(a.status);
    return `
    <div class="inspector-cita-card triage-border-${tri.toLowerCase()} ${done ? 'is-done' : ''}">
      <div class="inspector-cita-top">
        <span class="inspector-cita-time">${_formatTime12h(a.time)}</span>
        <span class="triage-mini triage-mini-${tri.toLowerCase()}" title="Prioridad de triaje">${tri}</span>
        ${a.wearable ? `<span class="inspector-wearable-chip">⌚ ${a.wearableText ? _escCal(a.wearableText) : 'Wearable conectado'}</span>` : ''}
      </div>
      <div class="inspector-cita-patient">${_escCal(a.patientName)}</div>
      ${a.curp ? `<div class="inspector-cita-curp">CURP: ${_escCal(a.curp)}</div>` : ''}
      <div class="inspector-cita-reason">${_escCal(a.reason)}</div>
      <div class="inspector-cita-controls">
        <label>Estado
          <select class="appt-inline-select" onchange="updateAppointmentField('${a.id}', { status: this.value })">
            ${APPT_STATUS_OPTIONS.map(s => `<option value="${s}" ${a.status === s ? 'selected' : ''}>${s}</option>`).join('')}
          </select>
        </label>
        <label>Triaje
          <select class="appt-inline-select" onchange="updateAppointmentField('${a.id}', { triage: this.value })">
            ${APPT_TRIAGE_OPTIONS.map(t => `<option value="${t}" ${tri === t ? 'selected' : ''}>${t}</option>`).join('')}
          </select>
        </label>
      </div>
      <div class="inspector-cita-actions">
        ${done ? '' : `<button class="btn-dark-pill" onclick="startConsultationFromAppt('${a.id}')">▶ Iniciar Consulta</button>`}
        ${a.curp ? `<button class="btn-outline-pill" onclick="openPatientProfile('${_escCal(a.curp)}')">Expediente</button>` : ''}
        <button class="btn-delete-cita" onclick="deleteAppointment('${a.id}')" title="Cancelar / eliminar cita">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
        </button>
      </div>
    </div>
  `;
  }).join('');
}

async function startConsultationFromAppt(apptId) {
  const appt = CalendarState.appointments.find(a => a.id === apptId);
  if (!appt) return;
  if (!String(apptId).startsWith('appt-')) {
    updateAppointmentField(apptId, { status: 'En Consulta' });
  }
  AppState.activeAppointmentId = apptId;

  let vitalsText = '';
  if (appt.curp && typeof fetchLatestVitalsText === 'function') {
    vitalsText = await fetchLatestVitalsText(appt.curp);
  }
  const presetText = `Paciente ${appt.patientName} acude a consulta agendada (${_formatTime12h(appt.time)}). Motivo: ${appt.reason}.${vitalsText ? ' ' + vitalsText : ''}`;
  startQuickConsultation(appt.curp || '', appt.patientName, presetText);
}

async function deleteAppointment(apptId) {
  const appt = CalendarState.appointments.find(a => a.id === apptId);
  if (!confirm(`¿Eliminar la cita de ${appt ? appt.patientName : 'este paciente'}?`)) return;
  try {
    if (!String(apptId).startsWith('appt-')) {
      const res = await fetch(`${API}/api/appointments/${encodeURIComponent(apptId)}`, { method: 'DELETE' });
      if (!res.ok && res.status !== 404) throw new Error('No se pudo eliminar la cita');
    }
    CalendarState.appointments = CalendarState.appointments.filter(a => a.id !== apptId);
    saveAppointmentsToStorage();
    renderCalendar();
    if (typeof refreshDashboardAgenda === 'function') refreshDashboardAgenda();
    showToast('Cita eliminada de la agenda', 'info');
  } catch (e) {
    showToast(e.message, 'error');
  }
}

async function openAppointmentModal(presetDateStr) {
  const overlay = document.getElementById('appointment-modal-overlay');
  if (!overlay) return;

  const dateInput = document.getElementById('appt-date');
  if (dateInput) dateInput.value = presetDateStr || CalendarState.selectedDateStr || _getTodayStr();

  const nameInput = document.getElementById('appt-patient-name');
  const curpInput = document.getElementById('appt-patient-curp');
  const reasonInput = document.getElementById('appt-reason');
  const wearableCheck = document.getElementById('appt-wearable');
  if (nameInput) nameInput.value = '';
  if (curpInput) curpInput.value = '';
  if (reasonInput) reasonInput.value = '';
  if (wearableCheck) wearableCheck.checked = false;

  // Populate patient dropdown from backend
  const select = document.getElementById('appt-patient-select');
  if (select) {
    select.innerHTML = '<option value="">— Escribir paciente manualmente o seleccionar —</option>';
    try {
      const res = await fetch(`${API}/api/patients/`);
      if (res.ok) {
        const patients = await res.json();
        patients.forEach(p => {
          const nombre = p.nombre || p.nombre_completo || p.curp;
          const opt = document.createElement('option');
          opt.value = JSON.stringify({ nombre, curp: p.curp });
          opt.textContent = `${nombre} (${p.curp})`;
          select.appendChild(opt);
        });
      }
    } catch { /* fallback to manual entry */ }
  }

  overlay.classList.add('open');
}

function closeAppointmentModal() {
  document.getElementById('appointment-modal-overlay')?.classList.remove('open');
}

function onApptPatientSelect(selectEl) {
  if (!selectEl.value) return;
  try {
    const data = JSON.parse(selectEl.value);
    document.getElementById('appt-patient-name').value = data.nombre || '';
    document.getElementById('appt-patient-curp').value = data.curp || '';
  } catch { /* ignore */ }
}

async function saveNewAppointment() {
  const patientName = document.getElementById('appt-patient-name')?.value.trim();
  const curp = document.getElementById('appt-patient-curp')?.value.trim().toUpperCase();
  const date = document.getElementById('appt-date')?.value;
  const time = document.getElementById('appt-time')?.value || '10:00';
  const reason = document.getElementById('appt-reason')?.value.trim();
  const wearable = document.getElementById('appt-wearable')?.checked || false;
  const triage = document.getElementById('appt-triage')?.value || 'VERDE';
  const status = document.getElementById('appt-status')?.value || 'Programada';

  if (!patientName || !date || !reason) {
    showToast('Completa el nombre del paciente, fecha y motivo de la cita', 'error');
    return;
  }

  // Evitar empalmes: misma fecha y hora
  const clash = CalendarState.appointments.find(a => a.date === date && a.time === time && !['Atendida', 'No asistió'].includes(a.status));
  if (clash && !confirm(`Ya existe una cita a las ${_formatTime12h(time)} con ${clash.patientName}. ¿Agendar de todos modos?`)) {
    return;
  }

  try {
    const res = await fetch(`${API}/api/appointments/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        patientName, curp, date, time, reason, wearable, triage, status,
        wearableText: wearable ? 'Wearable vinculado' : '',
      }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'No se pudo guardar la cita');
    }
    const created = await res.json();
    CalendarState.appointments.push(created);
    saveAppointmentsToStorage();
  } catch (e) {
    showToast(`Error: ${e.message}`, 'error');
    return;
  }

  const [y, m] = date.split('-').map(Number);
  CalendarState.year = y;
  CalendarState.month = m - 1;
  CalendarState.selectedDateStr = date;

  closeAppointmentModal();
  renderCalendar();
  if (typeof refreshDashboardAgenda === 'function') refreshDashboardAgenda();
  showToast(`Cita agendada para ${patientName} el ${_formatDateTitleES(date)}`, 'success');
}

function _escCal(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

document.addEventListener('DOMContentLoaded', () => {
  loadAppointments();
});
