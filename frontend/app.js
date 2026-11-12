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
  const btnAgnd = document.getElementById('nav-btn-agenda');
  const btnRep  = document.getElementById('nav-btn-reportes');
  const btnIa   = document.getElementById('nav-btn-ia-tools');
  const btnCfg  = document.getElementById('nav-btn-config');

  if (btnDash) btnDash.classList.toggle('active', tab === 'dashboard');
  if (btnCons) btnCons.classList.toggle('active', tab === 'consulta');
  if (btnExpe) btnExpe.classList.toggle('active', tab === 'expedientes');
  if (btnAgnd) btnAgnd.classList.toggle('active', tab === 'agenda');
  if (btnRep)  btnRep.classList.toggle('active', tab === 'reportes');
  if (btnIa)   btnIa.classList.toggle('active', tab === 'herramientas');
  if (btnCfg)  btnCfg.classList.toggle('active', tab === 'config');

  document.body.className = `mode-${tab}`;

  const dashSection = document.getElementById('panel-dashboard-section');
  const consultaLayout = document.getElementById('consulta-layout');
  const patientSection = document.getElementById('panel-patients-section');
  const agendaSection = document.getElementById('panel-agenda-section');
  const reportsSection = document.getElementById('panel-reports-section');
  const toolsSection = document.getElementById('panel-herramientas-section');
  const configSection = document.getElementById('panel-config-section');

  if (dashSection) {
    dashSection.style.display = tab === 'dashboard' ? 'block' : 'none';
    if (tab === 'dashboard' && typeof refreshDashboard === 'function') refreshDashboard();
  }
  if (reportsSection) {
    reportsSection.style.display = tab === 'reportes' ? 'block' : 'none';
    if (tab === 'reportes' && typeof renderReportsView === 'function') renderReportsView();
  }
  if (toolsSection) {
    toolsSection.style.display = tab === 'herramientas' ? 'block' : 'none';
    if (tab === 'herramientas' && typeof initHerramientasView === 'function') initHerramientasView();
  }
  if (configSection) {
    configSection.style.display = tab === 'config' ? 'block' : 'none';
    if (tab === 'config' && typeof loadSecurityConfigView === 'function') loadSecurityConfigView();
  }
  if (consultaLayout) consultaLayout.style.display = tab === 'consulta' ? 'grid' : 'none';
  if (patientSection) {
    patientSection.style.display = tab === 'expedientes' ? 'flex' : 'none';
    if (tab === 'expedientes') loadPatients();
  }
  if (agendaSection) {
    agendaSection.style.display = tab === 'agenda' ? 'block' : 'none';
    if (tab === 'agenda' && typeof renderCalendar === 'function') {
      renderCalendar();
    }
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
          .receta-alarma-box { margin-top: 14px; padding: 10px 14px; background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px; }
          .receta-alarma-box h6 { margin: 0 0 6px; font-size: 12px; color: #b91c1c; }
          .receta-alarma-box ul { margin: 0; padding-left: 18px; font-size: 11px; color: #7f1d1d; }
          .receta-footer-qr { display: flex; justify-content: space-between; align-items: flex-end; gap: 20px; margin-top: 22px; }
          .receta-qr-wrap { display: flex; align-items: center; gap: 10px; }
          .receta-qr-box svg { width: 76px; height: 76px; border: 1px solid #e5e7eb; border-radius: 6px; }
          .receta-qr-meta { font-size: 10px; color: #475569; display: flex; flex-direction: column; gap: 2px; }
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

  // 6. Guardián Clínico CDSS, DDx, Evidencia Vinculada y QR + Alarma en Receta
  renderClinicalSafetyAndInsights(data);
}

function renderClinicalSafetyAndInsights(data) {
  const seg = data.seguridad_clinica || {};
  const bannerEl = document.getElementById('clinical-safety-banner');
  if (bannerEl) {
    const tri = seg.triaje || {};
    const nivel = tri.nivel || 'VERDE';
    const flags = seg.banderas_rojas || [];
    const medAlerts = seg.alertas_medicamentos || [];
    const calc = seg.calculos_clinicos || {};
    const imc = calc.imc;

    const badgeCls = nivel === 'ROJO' ? 'triage-red'
                   : nivel === 'NARANJA' ? 'triage-orange'
                   : nivel === 'AMARILLO' ? 'triage-yellow' : 'triage-green';

    let alertsHtml = '';
    medAlerts.forEach(a => {
      const isCrit = a.severidad === 'CRITICA';
      alertsHtml += `
        <div class="cdss-alert-card ${isCrit ? 'cdss-crit' : 'cdss-warn'}">
          <div class="cdss-alert-head">
            <span class="cdss-sev-pill">${esc(a.severidad)}</span>
            <strong>${esc(a.medicamento)}: ${esc(a.titulo)}</strong>
          </div>
          <p>${esc(a.detalle)}</p>
          <div class="cdss-rec"><strong>Acción recomendada:</strong> ${esc(a.recomendacion)}</div>
        </div>`;
    });
    flags.forEach(rf => {
      alertsHtml += `
        <div class="cdss-alert-card cdss-flag">
          <div class="cdss-alert-head">
            <span class="cdss-sev-pill">${esc(rf.codigo)}</span>
            <strong>${esc(rf.titulo)}</strong>
          </div>
          <div class="cdss-rec"><strong>Protocolo inmediato:</strong> ${esc(rf.accion_inmediata)}</div>
        </div>`;
    });

    bannerEl.innerHTML = `
      <div class="cdss-top-row">
        <div class="cdss-triage-wrap">
          <span class="triage-badge ${badgeCls}">TRIAJE ${esc(nivel)} (ESI ${tri.codigo_esi || 4})</span>
          <span class="triage-meta">${esc(tri.etiqueta || '')} &bull; Espera máx: <strong>${esc(tri.tiempo_espera_max || '—')}</strong></span>
        </div>
        <div class="cdss-scores-row">
          <span class="cdss-score-chip">NEWS2: <strong>${calc.news2 ?? 0}</strong></span>
          <span class="cdss-score-chip">qSOFA: <strong>${calc.qsofa ?? 0}/3</strong></span>
          ${imc ? `<span class="cdss-score-chip">IMC: <strong>${imc.valor}</strong> (${esc(imc.categoria)})</span>` : ''}
        </div>
      </div>
      ${alertsHtml ? `<div class="cdss-alerts-stack">${alertsHtml}</div>` : '<div class="cdss-ok-strip">✅ Sin alergias cruzadas ni interacciones farmacológicas críticas detectadas.</div>'}
    `;
    bannerEl.style.display = 'block';
  }

  // DDx 3 niveles
  const ddxSec = document.getElementById('result-section-ddx');
  const ddxEl = document.getElementById('result-ddx');
  const ddxList = data.diagnostico_diferencial || [];
  if (ddxSec && ddxEl) {
    if (ddxList.length > 0) {
      ddxEl.innerHTML = ddxList.map(item => {
        const lvl = (item.nivel || 'Principal').toLowerCase();
        const lvlCls = lvl.includes('grave') || lvl.includes('descartar') ? 'ddx-grave' : lvl.includes('alternativo') ? 'ddx-alt' : 'ddx-pri';
        return `
          <div class="ddx-card ${lvlCls}">
            <div class="ddx-card-top">
              <span class="ddx-level">${esc(item.nivel || 'Principal')}</span>
              <strong>${esc(item.condicion || '')}</strong>
            </div>
            <p>${esc(item.justificacion || '')}</p>
            ${item.accion_descarte ? `<div class="ddx-action"><span>Sugerencia:</span> ${esc(item.accion_descarte)}</div>` : ''}
          </div>`;
      }).join('');
      ddxSec.style.display = 'block';
    } else {
      ddxSec.style.display = 'none';
    }
  }

  // Evidencia Vinculada
  const evSec = document.getElementById('result-section-evidence');
  const evEl = document.getElementById('result-evidence');
  const evList = data.evidencia_vinculada || [];
  if (evSec && evEl) {
    if (evList.length > 0) {
      evEl.innerHTML = evList.map(ev => `
        <div class="evidence-item">
          <span class="evidence-cat">${esc(ev.categoria)}</span>
          <strong class="evidence-ent">${esc(ev.entidad)}</strong>
          <span class="evidence-quote">“${esc(ev.cita_textual)}”</span>
        </div>`).join('');
      evSec.style.display = 'block';
    } else {
      evSec.style.display = 'none';
    }
  }

  // Signos de alarma en casa + QR en Receta
  const alarmaBox = document.getElementById('receta-alarma-box');
  const alarmaList = document.getElementById('receta-alarma-list');
  const homeWarnings = seg.signos_alarma_casa || [];
  if (alarmaBox && alarmaList) {
    if (homeWarnings.length > 0) {
      alarmaList.innerHTML = homeWarnings.map(w => `<li>${esc(w)}</li>`).join('');
      alarmaBox.style.display = 'block';
    } else {
      alarmaBox.style.display = 'none';
    }
  }

  const qrBox = document.getElementById('receta-qr-box');
  const verifEl = document.getElementById('receta-verif-code');
  if (qrBox && data.receta_qr_svg) {
    qrBox.innerHTML = data.receta_qr_svg;
  }
  if (verifEl) {
    verifEl.textContent = data.codigo_verificacion || 'MED-BORRADOR';
  }
}

/* ── PATIENTS DIRECTORY & SEARCH ── */
async function loadPatients() {
  try {
    const res = await fetch(`${API}/api/patients/`);
    const patients = await res.json();
    AppState.allPatients = Array.isArray(patients) ? patients : [];

    const activeQuery = (document.getElementById('search-input')?.value || '').trim();
    if (activeQuery) {
      handleSearch();
    } else {
      renderPatients(AppState.allPatients);
    }
  } catch {
    const listEl = document.getElementById('patients-list');
    if (listEl) listEl.innerHTML = '<div class="no-patients">Error al cargar pacientes</div>';
  }
}

function renderPatients(patients, isSemantic = false, emptyQuery = '') {
  const el = document.getElementById('patients-list');
  if (!patients.length) {
    const msg = emptyQuery
      ? `No se encontraron pacientes que coincidan con "${esc(emptyQuery)}".`
      : (isSemantic ? 'No se encontraron coincidencias semánticas.' : 'Sin pacientes registrados.');
    el.innerHTML = `<div class="no-patients">${msg}</div>`;
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
    return `
      <div class="patient-row" data-curp="${esc(curp)}" onclick="openPatientProfile('${esc(curp)}')" role="button" tabindex="0">
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
          <button class="patient-row-actions-btn" onclick="event.stopPropagation(); openPatientProfile('${esc(curp)}')" title="Abrir expediente">
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

function _normSearchText(str) {
  return String(str || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .trim();
}

function _tokenEditDistance(a, b) {
  const m = a.length;
  const n = b.length;
  if (Math.abs(m - n) > 2) return 99;
  const dp = Array.from({ length: m + 1 }, () => new Array(n + 1).fill(0));
  for (let i = 0; i <= m; i++) dp[i][0] = i;
  for (let j = 0; j <= n; j++) dp[0][j] = j;
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      dp[i][j] = Math.min(dp[i - 1][j] + 1, dp[i][j - 1] + 1, dp[i - 1][j - 1] + cost);
      if (i > 1 && j > 1 && a[i - 1] === b[j - 2] && a[i - 2] === b[j - 1]) {
        dp[i][j] = Math.min(dp[i][j], dp[i - 2][j - 2] + 1);
      }
    }
  }
  return dp[m][n];
}

function _filterPatientsLocally(patients, rawQuery) {
  const normQ = _normSearchText(rawQuery);
  if (!normQ) return patients;
  const qTokens = normQ.split(/\s+/).filter(Boolean);

  const scored = [];
  for (const p of patients) {
    const fullName = _normSearchText(
      p.nombre_completo || p.nombre || `${p.primer_apellido || ''} ${p.segundo_apellido || ''} ${p.nombres || ''}`
    );
    const curp = _normSearchText(p.curp);
    const folio = _normSearchText(p.folio_hospital);
    const searchable = `${fullName} ${curp} ${folio}`.trim();
    const docTokens = searchable.split(/[\s,.\-_/]+/).filter(Boolean);

    if (searchable.includes(normQ)) {
      scored.push({ p, score: 1000 });
      continue;
    }

    let totalScore = 0;
    let allMatched = true;
    for (const qt of qTokens) {
      let best = 0;
      for (const dt of docTokens) {
        if (dt === qt) { best = Math.max(best, 100); break; }
        if (dt.startsWith(qt)) { best = Math.max(best, 80); continue; }
        if (dt.includes(qt) && qt.length >= 3) { best = Math.max(best, 65); continue; }
        if (qt.length >= 4 && dt.length >= 4) {
          const dist = _tokenEditDistance(qt, dt);
          const maxAllowed = qt.length >= 6 ? 2 : 1;
          if (dist <= maxAllowed) {
            best = Math.max(best, 55 - dist * 10);
          }
        }
      }
      if (best === 0) {
        allMatched = false;
        break;
      }
      totalScore += best;
    }

    if (allMatched && totalScore > 0) {
      scored.push({ p, score: totalScore });
    }
  }

  scored.sort((a, b) => b.score - a.score);
  return scored.map(x => x.p);
}

function runQuickTopSearch(queryText) {
  const q = String(queryText || '').trim();
  const searchInp = document.getElementById('search-input');
  if (searchInp) searchInp.value = q;
  if (AppState.mainTab !== 'expedientes') {
    switchMainTab('expedientes');
  } else {
    handleSearch();
  }
}

/* Búsqueda */
let searchTimeout = null;
async function handleSearch() {
  const semCheck = document.getElementById('search-semantic-check');
  const isSemantic = !!(semCheck && semCheck.checked);
  const inputEl = document.getElementById('search-input');
  const q = (inputEl?.value || '').trim();

  // Mantener sincronizada la barra superior si el usuario escribe en el directorio
  const topInp = document.getElementById('global-quick-search');
  if (topInp && document.activeElement === inputEl) {
    topInp.value = inputEl.value;
  }

  if (!q) {
    if (Array.isArray(AppState.allPatients) && AppState.allPatients.length) {
      renderPatients(AppState.allPatients);
    } else {
      loadPatients();
    }
    return;
  }

  if (isSemantic) {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(async () => {
      try {
        const res = await fetch(`${API}/api/patients/search/semantic?q=${encodeURIComponent(q)}`);
        const results = await res.json();
        const filtered = Array.isArray(results) ? results.filter(r => (r.similitud || 0) >= 0.25) : [];
        renderPatients(filtered, true, q);
      } catch (err) { console.error(err); }
    }, 350);
  } else {
    if (!Array.isArray(AppState.allPatients)) {
      await loadPatients();
      return;
    }
    const filtered = _filterPatientsLocally(AppState.allPatients, q);
    renderPatients(filtered, false, q);
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
  const current = html.getAttribute('data-theme') || 'light';
  const next = current === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  localStorage.setItem('medicaition-theme-v5', next);
}

function _applyStoredTheme() {
  const saved = localStorage.getItem('medicaition-theme-v5') || 'light';
  document.documentElement.setAttribute('data-theme', saved);
}

/* ── DASHBOARD BENTO INTERACTIONS (Agenda, Wearables, Boceto Rápido) ── */
function startQuickConsultation(curp, patientName, sampleText) {
  switchMainTab('consulta');
  const curpEl = document.getElementById('curp-input');
  if (curpEl && curp) curpEl.value = curp;
  if (sampleText) {
    setMode('text');
    const txtEl = document.getElementById('text-input');
    if (txtEl) txtEl.value = sampleText;
  }
  showToast(`Consulta iniciada para ${patientName}`, 'success');
}

function openWearableModal() {
  document.getElementById('wearable-modal-overlay')?.classList.add('open');
}

function closeWearableModal() {
  document.getElementById('wearable-modal-overlay')?.classList.remove('open');
}

function importWearableHealthData() {
  switchMainTab('consulta');
  setMode('text');
  const curpEl = document.getElementById('curp-input');
  if (curpEl && !curpEl.value.trim()) {
    curpEl.value = 'GOPC790814HYNCLN04';
  }
  const txtEl = document.getElementById('text-input');
  const vitalsNote = 'Signos vitales sincronizados desde Smartwatch (Garmin Active / BLE): Presión arterial 122/78 mmHg, frecuencia cardíaca 72 lpm, frecuencia respiratoria 16 rpm, temperatura 36.5 °C, saturación de oxígeno 98%. ';
  if (txtEl) {
    txtEl.value = vitalsNote + (txtEl.value ? txtEl.value : 'Paciente masculino de 47 años en consulta de seguimiento. Consciente, orientado, campos pulmonares bien ventilados, abdomen blando depresible sin dolor.');
  }
  showToast('Datos biométricos del reloj importados a la consulta', 'success');
}

let _quickDictationActive = false;
function toggleQuickDictation() {
  const btn = document.getElementById('quick-voice-btn');
  const wave = document.getElementById('quick-waveform');
  const status = document.getElementById('quick-dictation-status');
  const input = document.getElementById('quick-dictation-input');

  _quickDictationActive = !_quickDictationActive;
  if (_quickDictationActive) {
    btn?.classList.add('dictating');
    wave?.classList.add('active-wave');
    if (status) status.textContent = '🔴 Escuchando dictado clínico en vivo (NOM-004)...';
    if (input && input.value.includes('45 años refiere dolor...')) {
      input.value = 'Paciente masculino de 45 años refiere dolor de cabeza moderado, sed intensa y cansancio de 4 días. Presión 135/85, frecuencia cardíaca 78, respiratoria 18, temperatura 36.6, oxígeno 98%. Bien orientado, abdomen blando no doloroso. Diagnóstico de diabetes mellitus tipo 2 en ajuste con metformina 850 mg cada 12 horas.';
    }
    showToast('Dictado rápido IA activado', 'info');
  } else {
    btn?.classList.remove('dictating');
    wave?.classList.remove('active-wave');
    if (status) status.textContent = 'Dictado IA capturado — Listo para estructurar NOM-004';
    showToast('Dictado capturado. Procesando nota...', 'success');
    processQuickNote();
  }
}

function processQuickNote() {
  const input = document.getElementById('quick-dictation-input');
  const text = input?.value?.trim() || 'Paciente masculino de 45 años refiere dolor de cabeza moderado. Presión 130/85, frecuencia cardíaca 76, temperatura 36.5, oxígeno 98%.';
  switchMainTab('consulta');
  setMode('text');
  const txtEl = document.getElementById('text-input');
  if (txtEl) txtEl.value = text;
  const curpEl = document.getElementById('curp-input');
  if (curpEl && !curpEl.value.trim()) curpEl.value = 'GOPC790814HYNCLN04';
  submitData();
}

function focusAgendaSection() {
  switchMainTab('dashboard');
  const card = document.getElementById('bento-agenda-card');
  if (card) {
    card.scrollIntoView({ behavior: 'smooth', block: 'center' });
    card.style.boxShadow = '0 0 0 3px #3b82f6, 0 12px 32px rgba(59, 130, 246, 0.2)';
    setTimeout(() => { card.style.boxShadow = ''; }, 1800);
  }
}

function focusEpidemiologiaSection() {
  switchMainTab('dashboard');
  const card = document.getElementById('bento-epidemiologia-card');
  if (card) {
    card.scrollIntoView({ behavior: 'smooth', block: 'center' });
    showToast('Alertas epidemiológicas en tiempo real — Yucatán (SINAVE / IA)', 'info');
  }
}

function focusTasksSection() {
  switchMainTab('dashboard');
  const card = document.getElementById('bento-tasks-card');
  if (card) {
    card.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
}

/* ── INITIALIZATION ── */
document.addEventListener('DOMContentLoaded', () => {
  _applyStoredTheme();
  switchMainTab(AppState.mainTab || 'dashboard');
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
          if (typeof loadActiveOperatorProfile === 'function') loadActiveOperatorProfile();
          if (typeof loadAppointments === 'function') loadAppointments();
          if (typeof refreshDashboard === 'function') refreshDashboard();
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
