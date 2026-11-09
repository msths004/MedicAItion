/**
 * app.js — MedicAItion v3.0
 * =========================================
 * Coordinador principal de la aplicación.
 * Las funciones grandes de overlay/modales/estado viven en:
 *   - state.js      → AppState (estado global)
 *   - overlays.js   → OverlaySystem (navegación Perfil → Eventos → Consultas)
 *   - modals.js     → Modales de formularios (Crear Evento, Asociar Nota, Registrar)
 *
 * Este archivo maneja: navegación principal, modo de entrada, grabación de audio,
 * pipeline de procesamiento, renderizado de resultados y carga del Gestor de Pacientes.
 */

/* ── MAIN NAVIGATION SWITCHING ── */
function switchMainTab(tab) {
  AppState.mainTab = tab;

  const btnDash = document.getElementById('nav-btn-dashboard');
  const btnCons = document.getElementById('nav-btn-consulta');
  const btnExpe = document.getElementById('nav-btn-expedientes');

  if (btnDash) btnDash.classList.toggle('active', tab === 'dashboard');
  if (btnCons) btnCons.classList.toggle('active', tab === 'consulta');
  if (btnExpe) btnExpe.classList.toggle('active', tab === 'expedientes');

  document.body.className = `mode-${tab}`;

  const dashSection = document.getElementById('panel-dashboard-section');
  const consultaLayout = document.getElementById('consulta-layout');
  const patientSection = document.getElementById('panel-patients-section');

  if (dashSection) dashSection.style.display = tab === 'dashboard' ? 'block' : 'none';
  if (consultaLayout) consultaLayout.style.display = tab === 'consulta' ? 'grid' : 'none';
  if (patientSection) {
    patientSection.style.display = tab === 'expedientes' ? 'flex' : 'none';
    if (tab === 'expedientes') loadPatients();
  }

  const titleEl = document.getElementById('results-panel-title');
  const descEl  = document.getElementById('results-panel-desc');
  if (tab === 'consulta') {
    if (titleEl) titleEl.textContent = 'Previsualización de Notas';
    if (descEl)  descEl.textContent  = 'Sincronización en tiempo real con motor CIE-10';
  }
}

/* ── MODE TOGGLE (Audio / Text input) ── */
function setMode(mode) {
  AppState.currentMode = mode;
  document.getElementById('btn-audio').classList.toggle('active', mode === 'audio');
  document.getElementById('btn-text').classList.toggle('active', mode === 'text');
  document.getElementById('audio-panel').style.display = mode === 'audio' ? 'block' : 'none';
  document.getElementById('text-panel').style.display  = mode === 'text'  ? 'block' : 'none';
  // method-card style
  document.querySelectorAll('.method-card:not(.method-card-ia)').forEach(c => c.classList.remove('active'));
  if (mode === 'audio') document.getElementById('btn-audio').classList.add('active');
  if (mode === 'text')  document.getElementById('btn-text').classList.add('active');
}

/* ── LLM CONFIGURATION MODAL ── */
function openLlmModal() {
  document.getElementById('llm-modal-overlay').classList.add('open');
}

function closeLlmModal() {
  document.getElementById('llm-modal-overlay').classList.remove('open');
}

function setLlmMode(mode) {
  AppState.llmMode = mode;
  document.querySelectorAll('.llm-option').forEach(el => el.classList.remove('selected'));
  document.getElementById(`opt-${mode}`).classList.add('selected');
  const labels = { 'auto': 'Auto', 'claude': 'Claude', 'local': 'Local' };
  document.getElementById('llm-mode-label').textContent = labels[mode];
}

/* ── RESULTS TAB TOGGLE ── */
function setResultTab(tab) {
  AppState.currentResultTab = tab;
  document.getElementById('tab-original').classList.toggle('active', tab === 'original');
  document.getElementById('tab-nota').classList.toggle('active', tab === 'nota');
  document.getElementById('tab-receta').classList.toggle('active', tab === 'receta');

  document.getElementById('original-content').style.display = tab === 'original' ? 'block' : 'none';
  document.getElementById('nota-content').style.display     = tab === 'nota'     ? 'block' : 'none';
  document.getElementById('receta-content').style.display   = tab === 'receta'   ? 'block' : 'none';

  if (tab === 'nota' && AppState.lastProcessedCurp) {
    loadNotaMedica(AppState.lastProcessedCurp);
  }
}

/* ── NOTA MÉDICA (iframe) ── */
function loadNotaMedica(curp) {
  const iframe = document.getElementById('nota-iframe');
  if (AppState.lastProcessedRecord && AppState.lastProcessedRecord.nota_medica_html) {
    iframe.srcdoc = AppState.lastProcessedRecord.nota_medica_html;
    iframe.setAttribute('data-loaded-curp', curp || '');
    return;
  }
  const cleanCurp = (curp || '').trim().toUpperCase();
  const url = `${API}/api/input/nota-medica/${encodeURIComponent(cleanCurp)}`;
  if (iframe.getAttribute('data-loaded-curp') !== cleanCurp) {
    iframe.removeAttribute('srcdoc');
    iframe.src = url;
    iframe.setAttribute('data-loaded-curp', cleanCurp);
  }
}

/* ── PRINT LOGIC ── */
function printActiveTab() {
  if (AppState.currentResultTab === 'nota') {
    const iframe = document.getElementById('nota-iframe');
    if (iframe && iframe.src && iframe.src !== 'about:blank') {
      try {
        iframe.contentWindow.print();
      } catch {
        const pw = window.open(iframe.src, '_blank', 'width=900,height=700');
        if (pw) pw.addEventListener('load', () => setTimeout(() => pw.print(), 500));
      }
    } else {
      showToast('No hay nota médica para imprimir', 'error');
    }
  } else if (AppState.currentResultTab === 'receta') {
    const cardHtml = document.getElementById('receta-card').outerHTML;
    const pw = window.open('', '_blank', 'width=900,height=700');
    if (pw) {
      pw.document.write(`
        <html><head><title>Receta Médica — Cruz Roja Mérida</title>
        <style>
          body { background: white; color: #1a1a1a; padding: 30px; font-family: 'Inter', sans-serif; }
          .receta-card { border: none; max-width: 100%; box-shadow: none; padding: 0; }
          .receta-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #ef4444; padding-bottom: 12px; margin-bottom: 16px; }
          .receta-table { width: 100%; border-collapse: collapse; font-size: 12px; }
          .receta-table th { text-align: left; background: #f9fafb; padding: 8px 10px; font-weight: 600; border-bottom: 1px solid #e5e7eb; }
          .receta-table td { padding: 8px 10px; border-bottom: 1px solid #f3f4f6; }
          @media print { body { padding: 0; } }
        </style></head><body>
        ${cardHtml}
        <script>window.onload = function() { setTimeout(() => { window.print(); window.close(); }, 300); }<\/script>
        </body></html>
      `);
      pw.document.close();
    }
  } else {
    showToast('Esta pestaña no es imprimible', 'info');
  }
}

/* ── AUDIO RECORDER ── */
async function toggleRecord() {
  if (!AppState.isRecording) await startRecording();
  else stopRecording();
}

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    AppState.mediaRecorder = new MediaRecorder(stream);
    AppState.audioChunks = [];
    AppState.recordedBlob = null;

    AppState.mediaRecorder.ondataavailable = e => AppState.audioChunks.push(e.data);
    AppState.mediaRecorder.onstop = () => {
      AppState.recordedBlob = new Blob(AppState.audioChunks, { type: 'audio/webm' });
      const url = URL.createObjectURL(AppState.recordedBlob);
      const playback = document.getElementById('audio-playback');
      playback.src = url;
      document.getElementById('audio-preview').style.display = 'block';
    };

    AppState.mediaRecorder.start();
    AppState.isRecording = true;

    document.getElementById('record-btn').classList.add('recording');
    document.getElementById('record-label').textContent = 'Grabando...';
    document.getElementById('record-icon').innerHTML = `
      <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
        <rect x="6" y="6" width="12" height="12" rx="2"/>
      </svg>`;
    document.getElementById('record-timer').style.display = 'block';
    document.getElementById('wave-bars').classList.add('active');

    AppState.timerSeconds = 0;
    AppState.timerInterval = setInterval(() => {
      AppState.timerSeconds++;
      const m = String(Math.floor(AppState.timerSeconds / 60)).padStart(2, '0');
      const s = String(AppState.timerSeconds % 60).padStart(2, '0');
      document.getElementById('record-timer').textContent = `${m}:${s}`;
    }, 1000);

  } catch (err) {
    showToast('Error al acceder al micrófono: ' + err.message, 'error');
  }
}

function stopRecording() {
  if (AppState.mediaRecorder && AppState.isRecording) {
    AppState.mediaRecorder.stop();
    AppState.mediaRecorder.stream.getTracks().forEach(t => t.stop());
    AppState.isRecording = false;
    clearInterval(AppState.timerInterval);

    document.getElementById('record-btn').classList.remove('recording');
    document.getElementById('record-label').textContent = 'Audio capturado ✓';
    document.getElementById('record-icon').innerHTML = `
      <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="8"/></svg>`;
    document.getElementById('wave-bars').classList.remove('active');
  }
}

/* ── SUBMIT PIPELINE ── */
async function submitData() {
  const curp  = document.getElementById('curp-input').value.trim();
  const clues = document.getElementById('clues-input').value.trim();

  if (AppState.currentMode === 'audio' && !AppState.recordedBlob)
    return showToast('Graba un audio primero', 'error');
  if (AppState.currentMode === 'text' && !document.getElementById('text-input').value.trim())
    return showToast('Escribe el texto clínico', 'error');

  setLoading(true);

  try {
    let data;
    const apiKey = document.getElementById('api-key-input').value.trim();

    if (AppState.currentMode === 'audio') {
      const fd = new FormData();
      fd.append('audio', AppState.recordedBlob, 'audio.webm');
      fd.append('curp', curp);
      fd.append('clues', clues);
      fd.append('llm_mode', AppState.llmMode);
      if (apiKey) fd.append('api_key', apiKey);
      // Pasar el evento activo al pipeline si ya existe
      if (AppState.currentEventId) fd.append('event_id', AppState.currentEventId);
      const res = await fetch(`${API}/api/input/audio`, { method: 'POST', body: fd });
      if (!res.ok) throw new Error(await res.text());
      data = await res.json();
    } else {
      const fd = new FormData();
      fd.append('text', document.getElementById('text-input').value.trim());
      fd.append('curp', curp);
      fd.append('clues', clues);
      fd.append('llm_mode', AppState.llmMode);
      if (apiKey) fd.append('api_key', apiKey);
      if (AppState.currentEventId) fd.append('event_id', AppState.currentEventId);
      const res = await fetch(`${API}/api/input/text`, { method: 'POST', body: fd });
      if (!res.ok) throw new Error(await res.text());
      data = await res.json();
    }

    AppState.lastProcessedCurp = data.curp || curp;
    AppState.lastProcessedRecord = data; // Guardar borrador en memoria
    renderResults(data);
    loadPatients();

    // Mostrar el botón de asociar nota después de generar exitosamente
    document.getElementById('btn-associate-note').style.display = 'flex';

    showToast('Notas médicas generadas exitosamente', 'success');

  } catch (err) {
    showToast('Error: ' + err.message, 'error');
    console.error(err);
  } finally {
    setLoading(false);
  }
}

/* ── RENDER RESULTS ── */
function renderResults(data) {
  document.getElementById('empty-state').style.display = 'none';
  document.getElementById('results-tabs').style.display = 'flex';

  setResultTab('original');

  const iframe = document.getElementById('nota-iframe');
  if (data.nota_medica_html) {
    iframe.srcdoc = data.nota_medica_html;
    iframe.setAttribute('data-loaded-curp', data.curp || '');
  } else {
    iframe.removeAttribute('data-loaded-curp');
    iframe.removeAttribute('srcdoc');
    iframe.src = 'about:blank';
  }

  // 1. Texto original
  document.getElementById('result-text').textContent = data.texto_original || '—';

  // 1.1 Texto re-redactado
  const redactadoSec = document.getElementById('result-section-redactado');
  const redactadoText = document.getElementById('result-text-redactado');
  if (redactadoSec && redactadoText) {
    if (data.texto_redactado) {
      redactadoText.textContent = data.texto_redactado;
      redactadoSec.style.display = 'block';
    } else {
      redactadoSec.style.display = 'none';
    }
  }

  // 2. Demográficos tags
  const demo = data.datos_demograficos || {};
  const demoEl = document.getElementById('result-demo');
  demoEl.innerHTML = '';
  const demoFields = { nombre: 'Nombre', edad: 'Edad', sexo: 'Sexo', curp: 'CURP' };
  Object.entries(demoFields).forEach(([k, label]) => {
    if (demo[k]) demoEl.innerHTML += `<span class="tag tag-demo">${label}: ${esc(demo[k])}</span>`;
  });
  if (!demoEl.innerHTML)
    demoEl.innerHTML = '<span style="font-size:12px;color:var(--text-muted)">Sin datos demográficos detectados</span>';

  // 3. CIE-10 Codes
  const cie10El = document.getElementById('result-cie10');
  cie10El.innerHTML = '';
  const categories = {
    sintomas_referidos:      { label: 'Síntomas Referidos (CIE-10)' },
    diagnosticos_tentativos: { label: 'Diagnósticos Tentativos (CIE-10)' },
    tratamientos:            { label: 'Procedimientos (CIE-9MC)' },
  };

  const codes = data.codigos_cie10 || {};
  Object.entries(categories).forEach(([key, { label }]) => {
    const items = codes[key] || [];
    if (!items.length) return;
    let html = `<div class="cie10-category"><div class="cie10-label">${label}</div>`;
    items.forEach(item => {
      const sim = item.similitud || 0;
      const simCls = sim >= 0.75 ? 'sim-high' : sim >= 0.5 ? 'sim-mid' : 'sim-low';
      html += `
        <div class="cie10-item">
          <span class="cie10-code">${item.codigo || '—'}</span>
          <div class="cie10-info">
            <span class="cie10-desc">${item.descripcion || item.termino_original}</span>
            <span class="cie10-original">Término original: "${esc(item.termino_original)}"</span>
          </div>
          <span class="sim-badge ${simCls}">${Math.round(sim * 100)}%</span>
        </div>`;
    });
    html += '</div>';
    cie10El.innerHTML += html;
  });
  if (!cie10El.innerHTML)
    cie10El.innerHTML = '<span style="font-size:12px;color:var(--text-muted)">Sin entidades mapeadas</span>';

  // 4. JSON completo
  const displayData = { ...data };
  delete displayData.nota_medica_html;
  document.getElementById('result-json').textContent = JSON.stringify(displayData, null, 2);

  // 5. Receta
  const folio = data.event_id ? `EV-${data.event_id.substring(0, 8).toUpperCase()}` : 'BORRADOR';
  document.getElementById('receta-folio').textContent = `Folio: ${folio}`;
  document.getElementById('receta-fecha').textContent = `Fecha: ${formatDate(data.timestamp || new Date().toISOString())}`;
  document.getElementById('receta-paciente-nombre').textContent = demo.nombre || 'Paciente General';
  document.getElementById('receta-paciente-curp').textContent   = data.curp || 'No proporcionado';
  document.getElementById('receta-paciente-edad-sexo').textContent = `${demo.edad || '—'} / ${demo.sexo || '—'}`;

  const medsListEl = document.getElementById('receta-meds-list');
  medsListEl.innerHTML = '';
  const meds = data.medicamentos || (data.entidades_extraidas && data.entidades_extraidas.medicamentos) || [];
  if (meds.length > 0) {
    meds.forEach(med => {
      medsListEl.innerHTML += `
        <tr>
          <td><strong>${esc(med.nombre)}</strong></td>
          <td>${esc(med.dosis || '—')}</td>
          <td>${esc(med.via || '—')}</td>
          <td>${esc(med.periodicidad || '—')}</td>
          <td>${esc(med.duracion || '—')}</td>
        </tr>`;
    });
  } else {
    medsListEl.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#777;">No se prescribieron medicamentos específicos.</td></tr>';
  }

  const instructions = data.receta_paciente || 
                       (data.entidades_extraidas && data.entidades_extraidas.receta_paciente) ||
                       (data.nota_clinica && data.nota_clinica.plan_tratamiento) || 
                       data.plan_tratamiento || 
                       'Seguir indicaciones generales médicas.';
  document.getElementById('receta-instructions-text').textContent = instructions;
}

/* ── PATIENTS DIRECTORY & SEARCH ── */
async function loadPatients() {
  try {
    const res = await fetch(`${API}/api/patients/`);
    const patients = await res.json();
    renderPatients(patients);
  } catch {
    document.getElementById('patients-list').innerHTML =
      '<div class="no-patients">Error al cargar pacientes</div>';
  }
}

function renderPatients(patients, isSemantic = false) {
  const el = document.getElementById('patients-list');
  if (!patients.length) {
    el.innerHTML = `<div class="no-patients">${isSemantic ? 'No se encontraron coincidencias semánticas' : 'Sin pacientes registrados'}</div>`;
    return;
  }

  const mapPatient = (p) => {
    const curp = isSemantic ? p.patient_curp : p.curp;
    const nombre = isSemantic ? (p.nombre_paciente || 'Nombre no registrado') : (p.nombre || p.nombre_completo || 'Nombre no registrado');
    const sexo = p.sexo || '';
    const edad = p.edad != null ? `${p.edad} años` : '';
    const folio = p.folio_hospital || '';
    const fecha = formatDate(p.created_at);
    const simBadge = isSemantic ? `<span class="sim-badge sim-high" style="font-size:10px;">IA: ${Math.round((p.similitud||0) * 100)}%</span>` : '';
    const sexoIcon = sexo === 'Femenino' ? '&#9792;' : sexo === 'Masculino' ? '&#9794;' : '';
    return `
      <div class="patient-row" onclick="openPatientProfile('${esc(curp)}')" role="button" tabindex="0">
        <div class="pt-col-patient">
          <div class="patient-row-avatar">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
          </div>
          <div class="patient-row-info">
            <span class="patient-row-name">${esc(nombre)}</span>
            <span class="patient-row-meta">${sexo ? sexo : ''}${sexo && edad ? ' • 👤 ' : ''}${edad}</span>
            ${curp ? `<span class="patient-row-curp-badge">CURP: ${esc(curp)}</span>` : ''}
            ${simBadge}
          </div>
        </div>
        <div class="pt-col-id">
          <span class="patient-row-id">${folio || '—'}</span>
          ${folio ? '<span class="id-local-badge">ID LOCAL</span>' : ''}
        </div>
        <div class="pt-col-date">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0;"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
          <div>
            <div class="patient-row-date">${fecha}</div>
          </div>
        </div>
        <div class="pt-col-actions">
          <button class="patient-row-actions-btn" onclick="event.stopPropagation(); window.showToast?.('Opciones próximamente', 'info')" title="Opciones">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="5" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="12" cy="19" r="1"/></svg>
          </button>
        </div>
      </div>
    `;
  };

  el.innerHTML = patients.map(mapPatient).join('');
}

/* Abrir el perfil del paciente en el overlay */
function openPatientProfile(curp) {
  AppState.selectedPatientCurp = curp;
  OverlaySystem.open('patient-profile', { curp });
}

/* Búsqueda */
let searchTimeout = null;
function handleSearch() {
  const isSemantic = document.getElementById('search-semantic-check').checked;
  const q = document.getElementById('search-input').value.trim();

  if (isSemantic) {
    clearTimeout(searchTimeout);
    if (!q) { loadPatients(); return; }
    searchTimeout = setTimeout(async () => {
      try {
        const res = await fetch(`${API}/api/patients/search/semantic?q=${encodeURIComponent(q)}`);
        const results = await res.json();
        renderPatients(results, true);
      } catch (err) { console.error(err); }
    }, 400);
  } else {
    const queryUpper = q.toUpperCase();
    const cards = document.querySelectorAll('.patient-card');
    cards.forEach(c => {
      const curp = c.querySelector('.patient-curp')?.textContent || '';
      const name = c.querySelector('.patient-name')?.textContent || '';
      c.style.display = (curp.toUpperCase().includes(queryUpper) || name.toUpperCase().includes(queryUpper)) ? 'flex' : 'none';
    });
  }
}

/* ── LEGACY: CLINICAL HISTORY (Panel Expedientes lateral) ── */
async function loadPatient(curp) {
  AppState.selectedPatientCurp = curp;
  AppState.lastProcessedCurp   = curp;

  const pInfoEl = document.getElementById('history-patient-info');
  pInfoEl.style.display = 'flex';

  try {
    const patientRes = await fetch(`${API}/api/patients/${curp}`);
    if (patientRes.ok) {
      const patient = await patientRes.json();
      document.getElementById('history-patient-name').textContent = patient.nombre || patient.nombre_completo || 'Nombre no registrado';
      document.getElementById('history-patient-curp').textContent = patient.curp;
    }

    const eventsRes = await fetch(`${API}/api/patients/${curp}/events`);
    if (!eventsRes.ok) throw new Error('Error fetching patient events');

    AppState.currentPatientEvents = await eventsRes.json();
    renderEventsTree();
  } catch (err) {
    showToast('Error al cargar historial clínico', 'error');
    console.error(err);
  }
}

function renderEventsTree() {
  const container = document.getElementById('events-tree-list');
  if (!AppState.currentPatientEvents || AppState.currentPatientEvents.length === 0) {
    container.innerHTML = '<div class="empty-state">Sin eventos clínicos registrados</div>';
    return;
  }

  container.innerHTML = AppState.currentPatientEvents.map(event => {
    return `
      <div class="event-node" id="event-node-${event.id}">
        <div class="event-node-header">
          <div class="event-title-container">
            <span class="event-node-title">${esc(event.nombre_evento)}</span>
            <button class="edit-event-btn" onclick="_promptRenameEvento('${esc(event.id)}', '${esc(event.nombre_evento)}', '${esc(AppState.selectedPatientCurp)}', '')" title="Renombrar">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
            </button>
          </div>
          <span class="event-node-date">${formatDate(event.updated_at)} (${event.num_consultas || 0} consultas)</span>
        </div>
        <div class="event-node-consultations">
          <div class="consultation-item" onclick="OverlaySystem.open('event-consultas', { evento_id: '${esc(event.id)}', evento_nombre: '${esc(event.nombre_evento)}', curp: '${esc(AppState.selectedPatientCurp)}', nombre: '' })">
            <div class="consultation-meta">
              <span class="consultation-date">Ver ${event.num_consultas || 0} consulta${event.num_consultas !== 1 ? 's' : ''} →</span>
            </div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

/* ── EVENT STATUS INDICATOR ── */
function updateEventStatus(eventId, eventName) {
  AppState.currentEventId   = eventId;
  AppState.currentEventName = eventName;

  const indicator = document.getElementById('event-status-indicator');
  const textEl    = document.getElementById('event-status-text');

  if (eventId && eventName) {
    textEl.textContent = `Evento Clínico: ${eventName}`;
    indicator.classList.add('active');
  } else {
    textEl.textContent = 'Evento Clínico: Sin crear';
    indicator.classList.remove('active');
  }
}

/* ── SANITIZATION HELPER ── */
function esc(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

/* ── UTILITIES ── */
function setLoading(on) {
  const btn = document.getElementById('submit-btn');
  btn.disabled = on;
  document.getElementById('submit-label').style.display = on ? 'none'   : 'inline';
  document.getElementById('spinner').style.display      = on ? 'block'  : 'none';
  document.getElementById('status-text').textContent    = on ? 'Procesando...' : 'Sistema listo';
}

function formatDate(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' });
}

function showToast(msg, type = 'info') {
  const existing = document.querySelector('.toast');
  if (existing) existing.remove();
  const t = document.createElement('div');
  t.className = `toast toast-${type}`;
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

/* ── THEME TOGGLE ── */
function toggleTheme() {
  const html = document.documentElement;
  const current = html.getAttribute('data-theme') || 'dark';
  const next = current === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  localStorage.setItem('medicaition-theme', next);
}

function _applyStoredTheme() {
  const saved = localStorage.getItem('medicaition-theme');
  if (saved && saved !== 'dark') {
    document.documentElement.setAttribute('data-theme', saved);
  }
}

/* ── INITIALIZATION ── */
document.addEventListener('DOMContentLoaded', () => {
  _applyStoredTheme();
  waitForBackend();
});


function waitForBackend() {
  const loadingScreen = document.getElementById('loading-screen');
  const statusEl = document.getElementById('loading-status');
  const messages = [
    'Iniciando el sistema...',
    'Cargando motor de IA...',
    'Preparando bases de datos médicas...',
    'Casi listo...'
  ];
  let msgIndex = 0;

  const msgInterval = setInterval(() => {
    msgIndex = Math.min(msgIndex + 1, messages.length - 1);
    if (statusEl) statusEl.textContent = messages[msgIndex];
  }, 4000);

  function checkBackend() {
    fetch(`${API}/api/patients/`)
      .then(res => {
        if (res.ok) return res.json();
        throw new Error('not ready');
      })
      .then(() => {
        clearInterval(msgInterval);
        if (statusEl) statusEl.textContent = '¡Listo!';
        setTimeout(() => {
          loadingScreen.classList.add('hidden');
          loadPatients();
        }, 600);
      })
      .catch(() => setTimeout(checkBackend, 1500));
  }

  checkBackend();
}

// Cerrar el LLM modal con Escape (compatibilidad)
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    const llmOverlay = document.getElementById('llm-modal-overlay');
    if (llmOverlay?.classList.contains('open')) closeLlmModal();
  }
});
