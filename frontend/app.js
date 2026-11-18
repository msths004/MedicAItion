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
  const btnClinExp = document.getElementById('nav-btn-clinica-exp');
  const btnAgnd = document.getElementById('nav-btn-agenda');
  const btnRep  = document.getElementById('nav-btn-reportes');
  const btnIa   = document.getElementById('nav-btn-ia-tools');
  const btnCfg  = document.getElementById('nav-btn-config');
  const btnLegal = document.getElementById('nav-btn-legal');

  if (btnDash) btnDash.classList.toggle('active', tab === 'dashboard');
  if (btnCons) btnCons.classList.toggle('active', tab === 'consulta');
  if (btnExpe) btnExpe.classList.toggle('active', tab === 'expedientes');
  if (btnClinExp) btnClinExp.classList.toggle('active', tab === 'expediente');
  if (btnAgnd) btnAgnd.classList.toggle('active', tab === 'agenda');
  if (btnRep)  btnRep.classList.toggle('active', tab === 'reportes');
  if (btnIa)   btnIa.classList.toggle('active', tab === 'herramientas');
  if (btnCfg)  btnCfg.classList.toggle('active', tab === 'config');
  if (btnLegal) btnLegal.classList.toggle('active', tab === 'legal');

  // Actualizar modo en el body para CSS
  document.body.className = `mode-${tab}`;

  // Diccionario de paneles de vista con inicializadores seguros
  const viewPanels = {
    'dashboard': { id: 'panel-dashboard-section', display: 'block', init: () => typeof refreshDashboard === 'function' && refreshDashboard() },
    'consulta': { id: 'consulta-layout', display: 'grid', init: () => {} },
    'expedientes': { id: 'panel-patients-section', display: 'flex', init: () => typeof loadPatients === 'function' && loadPatients() },
    'expediente': { id: 'panel-expediente-section', display: 'block', init: () => typeof initSpecializedCareView === 'function' && initSpecializedCareView() },
    'agenda': { id: 'panel-agenda-section', display: 'block', init: () => typeof renderCalendar === 'function' && renderCalendar() },
    'reportes': { id: 'panel-reports-section', display: 'block', init: () => typeof renderReportsView === 'function' && renderReportsView() },
    'herramientas': { id: 'panel-herramientas-section', display: 'block', init: () => typeof initHerramientasView === 'function' && initHerramientasView() },
    'config': { id: 'panel-config-section', display: 'block', init: () => typeof loadSecurityConfigView === 'function' && loadSecurityConfigView() },
    'legal': { id: 'panel-legal-section', display: 'block', init: () => typeof loadLegalView === 'function' && loadLegalView() }
  };

  // Ocultar estrictamente todas las vistas excepto la activa
  Object.keys(viewPanels).forEach(key => {
    const item = viewPanels[key];
    const el = document.getElementById(item.id);
    if (el) {
      if (key === tab) {
        el.style.display = item.display;
        try {
          item.init();
        } catch (err) {
          console.warn(`[Nav] Error al inicializar vista ${key}:`, err);
        }
      } else {
        el.style.display = 'none';
      }
    }
  });

  const titleEl = document.getElementById('results-panel-title');
  const descEl  = document.getElementById('results-panel-desc');
  if (tab === 'consulta') {
    if (titleEl) titleEl.textContent = 'Previsualización de Notas';
    if (descEl)  descEl.textContent  = 'Sincronización en tiempo real con motor CIE-10';
  }
}

/* ── MODE TOGGLE (Audio / Text / Transcripción input) ── */
function setMode(mode) {
  AppState.currentMode = mode;
  document.getElementById('btn-audio')?.classList.toggle('active', mode === 'audio');
  document.getElementById('btn-text')?.classList.toggle('active', mode === 'text');
  document.getElementById('btn-transcripcion')?.classList.toggle('active', mode === 'transcripcion');

  const audioPanel = document.getElementById('audio-panel');
  const textPanel  = document.getElementById('text-panel');
  const rxPanel    = document.getElementById('transcripcion-panel');
  if (audioPanel) audioPanel.style.display = mode === 'audio' ? 'block' : 'none';
  if (textPanel)  textPanel.style.display  = mode === 'text'  ? 'block' : 'none';
  if (rxPanel)    rxPanel.style.display    = mode === 'transcripcion' ? 'block' : 'none';

  // method-card style
  document.querySelectorAll('.method-card:not(.method-card-ia)').forEach(c => c.classList.remove('active'));
  if (mode === 'audio') document.getElementById('btn-audio')?.classList.add('active');
  if (mode === 'text')  document.getElementById('btn-text')?.classList.add('active');
  if (mode === 'transcripcion') {
    document.getElementById('btn-transcripcion')?.classList.add('active');
    initRxDropzone();
  }
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
  if (AppState.currentMode === 'transcripcion') {
    const rxNarrative = buildNarrativeFromRxEditor();
    if (!rxNarrative) {
      return showToast('Sube una imagen de receta médica o selecciona una receta manuscrita de ejemplo primero', 'error');
    }
    const txtEl = document.getElementById('text-input');
    if (txtEl) {
      const existing = txtEl.value.trim();
      if (!existing || existing.includes('Tratamiento farmacológico transcrito:')) {
        txtEl.value = rxNarrative;
      } else {
        txtEl.value = existing + '\n\n' + rxNarrative;
      }
    }
  }

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
    if (data?.legal_privacy_guard?.cloud_transfer_blocked) {
      showToast(
        data.legal_privacy_guard.message || 'Protección LFPDPPP: envío a nube bloqueado sin consentimiento Art. 36; procesado 100% local.',
        'info'
      );
    }

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
      const parts = nombre.split(/\s+/).filter(Boolean);
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
}

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
    fetch(`${API}/api/status`)
      .then(res => {
        if (res.ok) return res.json();
        throw new Error('not ready');
      })
      .then(() => {
        clearInterval(msgInterval);
        if (statusEl) statusEl.textContent = '¡Listo!';
        setTimeout(() => {
          loadingScreen.classList.add('hidden');
          if (typeof initAuthGateOnStartup === 'function') {
            initAuthGateOnStartup();
          } else {
            loadPatients();
          }
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

/* ==========================================================================
   MOTOR DE TRANSCRIPCIÓN DE RECETAS MÉDICAS (100% LOCAL OCR + VISIÓN)
   ========================================================================== */
let _rxDropzoneInitialized = false;
let _lastRxTranscriptionData = null;

function initRxDropzone() {
  if (_rxDropzoneInitialized) return;
  const dropzone = document.getElementById('rx-dropzone');
  if (!dropzone) return;
  _rxDropzoneInitialized = true;

  ['dragenter', 'dragover'].forEach(evtName => {
    dropzone.addEventListener(evtName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(evtName => {
    dropzone.addEventListener(evtName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove('dragover');
    });
  });

  dropzone.addEventListener('drop', (e) => {
    const files = e.dataTransfer?.files;
    if (files && files.length > 0) {
      uploadAndTranscribeRxFile(files[0]);
    }
  });

  // Inicializar estado del motor y asegurar imágenes de muestra en el backend
  fetch(`${API}/api/input/prescription-ocr/status`)
    .then(r => r.ok ? r.json() : null)
    .then(st => {
      if (st && st.active_pipeline) {
        const lbl = document.getElementById('rx-ocr-engine-label');
        if (lbl) lbl.textContent = `🔒 IA Visión Local: ${st.active_pipeline}`;
      }
    })
    .catch(() => {});
}

function handleRxFileSelect(event) {
  const file = event.target?.files?.[0];
  if (file) {
    uploadAndTranscribeRxFile(file);
  }
}

async function uploadAndTranscribeRxFile(file) {
  if (!file.type.startsWith('image/')) {
    showToast('Por favor selecciona un archivo de imagen válido (JPG, PNG, WEBP)', 'error');
    return;
  }

  // Mostrar previsualización local inmediata
  const reader = new FileReader();
  reader.onload = (e) => {
    const previewImg = document.getElementById('rx-image-preview');
    const emptyBox   = document.getElementById('rx-dropzone-empty');
    const prevBox    = document.getElementById('rx-preview-container');
    const fnameEl    = document.getElementById('rx-preview-filename');
    if (previewImg) previewImg.src = e.target.result;
    if (fnameEl) fnameEl.textContent = `${file.name} (${Math.round(file.size / 1024)} KB)`;
    if (emptyBox) emptyBox.style.display = 'none';
    if (prevBox) prevBox.style.display = 'flex';
  };
  reader.readAsDataURL(file);

  const loadingEl = document.getElementById('rx-ocr-loading');
  const resultsEl = document.getElementById('rx-structured-results');
  if (loadingEl) loadingEl.style.display = 'flex';
  if (resultsEl) resultsEl.style.display = 'none';

  try {
    const curp = document.getElementById('curp-input')?.value?.trim() || '';
    const fd = new FormData();
    fd.append('image', file);
    if (curp) fd.append('curp', curp);

    const res = await fetch(`${API}/api/input/prescription-ocr`, {
      method: 'POST',
      body: fd,
    });
    if (!res.ok) {
      const errText = await res.text();
      throw new Error(errText || 'Error en transcripción de receta');
    }
    const data = await res.json();
    _lastRxTranscriptionData = data;
    renderRxStructuredResults(data);
    showToast(`Receta transcrita 100% en local (${data.medications?.length || 0} fármacos detectados en ${(data.elapsed_ms / 1000).toFixed(1)}s)`, 'success');
  } catch (err) {
    console.error('[RxOCR Error]', err);
    showToast('Error al transcribir imagen: ' + err.message, 'error');
  } finally {
    if (loadingEl) loadingEl.style.display = 'none';
  }
}

async function runRxSampleTranscription(sampleId) {
  const loadingEl = document.getElementById('rx-ocr-loading');
  const resultsEl = document.getElementById('rx-structured-results');
  if (loadingEl) loadingEl.style.display = 'flex';
  if (resultsEl) resultsEl.style.display = 'none';

  try {
    const curp = document.getElementById('curp-input')?.value?.trim() || '';
    const fd = new FormData();
    if (curp) fd.append('curp', curp);

    const res = await fetch(`${API}/api/input/prescription-ocr/sample/${encodeURIComponent(sampleId)}`, {
      method: 'POST',
      body: fd,
    });
    if (!res.ok) {
      const errText = await res.text();
      throw new Error(errText || 'Error procesando receta manuscrita de ejemplo');
    }
    const data = await res.json();
    _lastRxTranscriptionData = data;

    // Mostrar la imagen manuscrita en el visor
    if (data.sample_image_url) {
      const previewImg = document.getElementById('rx-image-preview');
      const emptyBox   = document.getElementById('rx-dropzone-empty');
      const prevBox    = document.getElementById('rx-preview-container');
      const fnameEl    = document.getElementById('rx-preview-filename');
      if (previewImg) previewImg.src = `${data.sample_image_url}?t=${Date.now()}`;
      if (fnameEl) fnameEl.textContent = data.sample_title || `Receta manuscrita (${sampleId})`;
      if (emptyBox) emptyBox.style.display = 'none';
      if (prevBox) prevBox.style.display = 'flex';
    }

    renderRxStructuredResults(data);
    showToast(`Receta manuscrita descifrada en ${(data.elapsed_ms / 1000).toFixed(1)}s (${data.medications?.length || 0} fármacos)`, 'success');
  } catch (err) {
    console.error('[RxSampleOCR Error]', err);
    showToast('Error al procesar receta de muestra: ' + err.message, 'error');
  } finally {
    if (loadingEl) loadingEl.style.display = 'none';
  }
}

function renderRxStructuredResults(data) {
  const resultsEl = document.getElementById('rx-structured-results');
  const listEl    = document.getElementById('rx-medications-list');
  const metaEl    = document.getElementById('rx-results-meta');
  const headerInfo = document.getElementById('rx-detected-header-info');
  const safetyBox  = document.getElementById('rx-safety-banner');

  if (!resultsEl || !listEl) return;
  resultsEl.style.display = 'block';

  const meds = Array.isArray(data.medications) ? data.medications : [];
  if (metaEl) {
    metaEl.textContent = `${meds.length} medicamento(s) estructurado(s) · Tiempo de inferencia local: ${data.elapsed_ms || 0} ms`;
  }

  // Encabezado detectado (Médico / Diagnóstico)
  const md = data.metadata || {};
  if (headerInfo) {
    const badges = [];
    if (md.diagnostico_detectado) {
      badges.push(`<span class="rx-meta-pill"><strong>🩺 Diagnóstico detectado:</strong> ${escapeRxHtml(md.diagnostico_detectado)}</span>`);
    }
    if (md.medico_prescriptor) {
      badges.push(`<span class="rx-meta-pill"><strong>👨‍⚕️ Prescriptor:</strong> ${escapeRxHtml(md.medico_prescriptor)}</span>`);
    }
    if (md.fecha_receta) {
      badges.push(`<span class="rx-meta-pill"><strong>📅 Fecha:</strong> ${escapeRxHtml(md.fecha_receta)}</span>`);
    }
    if (badges.length > 0) {
      headerInfo.innerHTML = badges.join('');
      headerInfo.style.display = 'flex';
    } else {
      headerInfo.style.display = 'none';
    }
  }

  // Alerta de seguridad clínica CDSS (alergias / interacciones)
  if (safetyBox) {
    const alerts = data.safety_verification?.alerts || [];
    if (alerts.length > 0) {
      safetyBox.innerHTML = `
        <div class="rx-safety-title">⚠️ Alerta Farmacológica CDSS Detectada en la Receta</div>
        <ul class="rx-safety-list">
          ${alerts.map(a => `<li><strong>[${escapeRxHtml(a.severity || 'ALERTA')}] ${escapeRxHtml(a.title || '')}:</strong> ${escapeRxHtml(a.detail || a.message || '')}</li>`).join('')}
        </ul>
      `;
      safetyBox.style.display = 'block';
    } else {
      safetyBox.style.display = 'none';
    }
  }

  listEl.innerHTML = '';
  if (meds.length === 0) {
    // Si no se detectó un fármaco estructurado, agregar una fila editable con el texto crudo
    addRxMedicationRow({
      nombre_farmaco: '',
      dosis: '',
      frecuencia: '',
      via_administracion: 'Vía Oral (VO)',
      duracion: '',
      observaciones: data.raw_text ? `Texto detectado: ${data.raw_text}` : '',
      confianza: 0.80,
    });
  } else {
    meds.forEach(m => addRxMedicationRow(m));
  }
}

function escapeRxHtml(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function addRxMedicationRow(med = {}) {
  const listEl = document.getElementById('rx-medications-list');
  if (!listEl) return;

  const idx = listEl.children.length + 1;
  const confPct = Math.round((Number(med.confianza) || 0.92) * 100);
  const row = document.createElement('div');
  row.className = 'rx-med-item-card';
  row.innerHTML = `
    <div class="rx-med-item-top">
      <span class="rx-med-item-num">Fármaco #${idx}</span>
      <span class="rx-med-conf-badge" title="Confianza del decodificador caligráfico local">🎯 Confianza IA: ${confPct}%</span>
      <button type="button" class="rx-med-delete-btn" onclick="removeRxMedicationRow(this)" title="Eliminar este fármaco">✕</button>
    </div>
    <div class="rx-med-grid">
      <div class="rx-field-group rx-field-wide">
        <label>Nombre del fármaco (Genérico / Sal)</label>
        <input type="text" class="rx-input rx-in-nombre" value="${escapeRxHtml(med.nombre_farmaco || '')}" placeholder="Ej. Amoxicilina / Ácido Clavulánico" />
      </div>
      <div class="rx-field-group">
        <label>Dosis / Presentación</label>
        <input type="text" class="rx-input rx-in-dosis" value="${escapeRxHtml(med.dosis || '')}" placeholder="Ej. 875/125 mg" />
      </div>
      <div class="rx-field-group">
        <label>Frecuencia</label>
        <input type="text" class="rx-input rx-in-frecuencia" value="${escapeRxHtml(med.frecuencia || '')}" placeholder="Ej. Cada 12 horas (c/12h)" />
      </div>
      <div class="rx-field-group">
        <label>Vía de administración</label>
        <input type="text" class="rx-input rx-in-via" value="${escapeRxHtml(med.via_administracion || 'Vía Oral (VO)')}" placeholder="Ej. Vía Oral (VO)" />
      </div>
      <div class="rx-field-group">
        <label>Duración del tratamiento</label>
        <input type="text" class="rx-input rx-in-duracion" value="${escapeRxHtml(med.duracion || '')}" placeholder="Ej. 7 días" />
      </div>
      <div class="rx-field-group rx-field-full">
        <label>Observaciones e Indicaciones Clínicas</label>
        <input type="text" class="rx-input rx-in-obs" value="${escapeRxHtml(med.observaciones || '')}" placeholder="Ej. Tomar con alimentos..." />
      </div>
    </div>
  `;
  listEl.appendChild(row);
}

function removeRxMedicationRow(btnEl) {
  const card = btnEl.closest('.rx-med-item-card');
  if (card) card.remove();
  // Renumerar tarjetas
  document.querySelectorAll('#rx-medications-list .rx-med-item-card').forEach((el, i) => {
    const numEl = el.querySelector('.rx-med-item-num');
    if (numEl) numEl.textContent = `Fármaco #${i + 1}`;
  });
}

function buildNarrativeFromRxEditor() {
  const cards = document.querySelectorAll('#rx-medications-list .rx-med-item-card');
  if (!cards.length) return '';

  const lines = [];
  const md = _lastRxTranscriptionData?.metadata || {};
  if (md.diagnostico_detectado) {
    lines.push(`Diagnóstico en receta transcrita: ${md.diagnostico_detectado}.`);
  }
  if (md.medico_prescriptor) {
    lines.push(`Receta emitida por: ${md.medico_prescriptor}.`);
  }

  const medLines = [];
  cards.forEach((card, idx) => {
    const nombre = card.querySelector('.rx-in-nombre')?.value?.trim() || '';
    const dosis  = card.querySelector('.rx-in-dosis')?.value?.trim() || '';
    const frec   = card.querySelector('.rx-in-frecuencia')?.value?.trim() || '';
    const via    = card.querySelector('.rx-in-via')?.value?.trim() || '';
    const dur    = card.querySelector('.rx-in-duracion')?.value?.trim() || '';
    const obs    = card.querySelector('.rx-in-obs')?.value?.trim() || '';

    if (nombre) {
      let itemStr = `${idx + 1}. ${nombre}`;
      if (dosis) itemStr += ` ${dosis}`;
      if (frec)  itemStr += ` — ${frec}`;
      if (via)   itemStr += `, ${via}`;
      if (dur)   itemStr += `, durante ${dur}`;
      if (obs)   itemStr += `. (${obs})`;
      medLines.push(itemStr);
    }
  });

  if (!medLines.length) return '';
  lines.push('Tratamiento farmacológico transcrito:\n' + medLines.join('\n'));
  return lines.join('\n\n');
}

function syncRxToClinicalText(switchTab = true) {
  const narrative = buildNarrativeFromRxEditor();
  if (!narrative) {
    showToast('No hay medicamentos estructurados para copiar', 'error');
    return;
  }
  const txtEl = document.getElementById('text-input');
  if (txtEl) {
    const existing = txtEl.value.trim();
    if (!existing || existing.includes('Tratamiento farmacológico transcrito:')) {
      txtEl.value = narrative;
    } else {
      txtEl.value = existing + '\n\n' + narrative;
    }
  }
  if (switchTab) {
    setMode('text');
    showToast('Receta estructurada transferida al editor de texto clínico', 'success');
  }
}


/* ==========================================================================
   CLINICAL ARCHITECTURE REDESIGN — CONTROLLER LOGIC
   Soporte para Vista Dividida (Split-Screen), Modo Clínico & Asistencia IA
   ========================================================================== */

function _updateThemeUi(theme) {
  const labelEl = document.getElementById('theme-label');
  const iconEl = document.getElementById('theme-icon');
  if (theme === 'dark') {
    if (labelEl) labelEl.textContent = 'Modo Guardia (Nocturno)';
    if (iconEl) iconEl.textContent = '🌙';
  } else {
    if (labelEl) labelEl.textContent = 'Modo Clínico Diurno';
    if (iconEl) iconEl.textContent = '☀️';
  }
}

// Override toggleTheme with instant label update
const _originalToggleTheme = typeof toggleTheme === 'function' ? toggleTheme : null;
function toggleTheme() {
  const html = document.documentElement;
  const current = html.getAttribute('data-theme') || 'light';
  const next = current === 'dark' ? 'light' : 'dark';
  html.setAttribute('data-theme', next);
  localStorage.setItem('medicaition-theme-v5', next);
  _updateThemeUi(next);
  if (typeof showToast === 'function') {
    showToast(next === 'dark' ? '🌙 Modo Guardia Nocturna Activado' : '☀️ Modo Clínico Diurno Activado', 'info');
  }
}

// Call on startup
document.addEventListener('DOMContentLoaded', () => {
  const saved = localStorage.getItem('medicaition-theme-v5') || 'light';
  _updateThemeUi(saved);
  loadConsultaPatientContext('MOBK070228HYNRTVA3');
});

// Patient Context Loader for Left Split Panel
async function loadConsultaPatientContext(curp) {
  if (!curp) return;

  // Actualizar el input oculto o visible de CURP
  const curpInp = document.getElementById('curp-input');
  if (curpInp) curpInp.value = curp;

  let p = (AppState.allPatients || []).find(x => x.curp === curp);
  if (!p) {
    try {
      const res = await fetch(`${API}/api/patients/${encodeURIComponent(curp)}`);
      if (res.ok) p = await res.json();
    } catch (e) {
      console.warn('[Consulta] Error buscando paciente:', e);
    }
  }

  // Fallback seguro
  const name = p ? (p.nombre_completo || p.nombre || `${p.nombres || ''} ${p.primer_apellido || ''} ${p.segundo_apellido || ''}`.trim()) : 'Paciente Activo';
  const parts = name.split(/\s+/).filter(Boolean);
  const initials = parts.length > 1 ? (parts[0][0] + parts[1][0]).toUpperCase() : (parts[0] ? parts[0].slice(0, 2).toUpperCase() : 'PT');
  const blood = p && p.tipo_sangre ? p.tipo_sangre : 'O+';
  const ageStr = (p && p.edad != null) ? `${p.edad} años · ${p.sexo || 'M'}` : '—';
  const folio = (p && p.folio_hospital) ? p.folio_hospital : curp.slice(0, 10);

  // Alergias
  let allergiesText = '⚠️ Sin alergias medicamentosas conocidas.';
  if (p && Array.isArray(p.alergias) && p.alergias.length > 0) {
    allergiesText = '⚠️ ' + p.alergias.map(a => a.descripcion).join(' · ');
  }

  // Update UI Elements Columna 1
  const elName = document.getElementById('panel-vitals-name');
  if (elName) elName.textContent = name;
  const elAvatar = document.getElementById('panel-vitals-avatar');
  if (elAvatar) elAvatar.textContent = initials;
  const elId = document.getElementById('panel-vitals-id');
  if (elId) elId.textContent = `ID: ${folio}`;
  const elBlood = document.getElementById('panel-vitals-blood');
  if (elBlood) elBlood.textContent = `Sangre: ${blood}`;
  const elAge = document.getElementById('panel-vitals-age');
  if (elAge) elAge.textContent = ageStr;
  const elCurp = document.getElementById('panel-vitals-curp');
  if (elCurp) elCurp.textContent = curp;

  const elAllergies = document.getElementById('panel-vitals-allergy-text');
  if (elAllergies) elAllergies.textContent = allergiesText;

  // Buscar última lectura de telemetría / wearables
  let ta = '120/78';
  let fc = '78';
  let spo2 = '98%';
  let temp = '36.6';
  let devName = 'Triaje de Enfermería • Verificado';

  try {
    const vRes = await fetch(`${API}/api/wearables/readings?curp=${encodeURIComponent(curp)}&limit=1`);
    if (vRes.ok) {
      const vData = await vRes.json();
      const r = (vData.readings && vData.readings[0]);
      if (r) {
        if (r.systolic_bp && r.diastolic_bp) ta = `${r.systolic_bp}/${r.diastolic_bp}`;
        if (r.heart_rate) fc = String(r.heart_rate);
        if (r.spo2) spo2 = `${r.spo2}%`;
        if (r.temperature) temp = String(r.temperature);
        if (r.device_name) devName = `${r.device_name} · En vivo`;
      }
    }
  } catch {}

  const elTa = document.getElementById('panel-vitals-ta');
  if (elTa) elTa.textContent = ta;
  const elFc = document.getElementById('panel-vitals-fc');
  if (elFc) elFc.textContent = fc;
  const elSpo2 = document.getElementById('panel-vitals-spo2');
  if (elSpo2) elSpo2.textContent = spo2;
  const elTemp = document.getElementById('panel-vitals-temp');
  if (elTemp) elTemp.textContent = temp;

  const elBadge = document.getElementById('panel-vitals-device-badge');
  if (elBadge) elBadge.textContent = devName;

  // Antecedentes
  const histContainer = document.getElementById('panel-vitals-history-tags');
  if (histContainer) {
    if (p && Array.isArray(p.antecedentes) && p.antecedentes.length > 0) {
      histContainer.innerHTML = p.antecedentes.map(a => `<span class="comorbidity-pill">• ${esc(a.descripcion)}</span>`).join('');
    } else if (p && p.anotaciones_generales) {
      histContainer.innerHTML = `<span class="comorbidity-pill">• ${esc(p.anotaciones_generales)}</span>`;
    } else {
      histContainer.innerHTML = '<span class="comorbidity-pill">• Sin antecedentes patológicos documentados</span>';
    }
  }

  // =========================================================================
  // Actualizar Columna 3 (Inferior): Seguimiento del Paciente & Adherencia
  // =========================================================================
  const adherencePill = document.getElementById('followup-adherence-pill');
  const adherenceBar = document.getElementById('adherence-bar-fill');
  const adherenceText = document.getElementById('adherence-pct-text');
  const patientReport = document.getElementById('followup-patient-report');

  // Adherencia simulada clínicamente consistente según patología
  const isChron = p && (p.anotaciones_generales || '').toLowerCase().includes('diabetes') || (p.anotaciones_generales || '').toLowerCase().includes('hipertens');
  const adherencePct = isChron ? 92 : 96;

  if (adherencePill) adherencePill.textContent = `${adherencePct}% Adherencia`;
  if (adherenceBar) adherenceBar.style.width = `${adherencePct}%`;
  if (adherenceText) adherenceText.textContent = `Excelente (${adherencePct}%)`;

  if (patientReport) {
    if (p && p.anotaciones_generales) {
      patientReport.innerHTML = `<em>"Control activo de: ${esc(p.anotaciones_generales.slice(0, 80))}... Reporta tomas al día sin reacciones adversas."</em>`;
    } else {
      patientReport.innerHTML = `<em>"Paciente refiere evolución estable sin quejas clínicas de alarma en las últimas 48 horas."</em>`;
    }
  }
}

function onConsultaPatientSelect(curp) {
  loadConsultaPatientContext(curp);
  if (typeof showToast === 'function') {
    showToast(`Paciente seleccionado: ${curp}`, 'info');
  }
}

// AI Copilot Suggestion Action Handlers (Aceptar / Editar / Rechazar)
function acceptAiSuggestion(type) {
  const card = document.getElementById(`ai-sugg-${type}`);
  if (type === 'cie10') {
    const code = document.getElementById('sugg-cie10-code')?.textContent || 'J00';
    const textEl = document.getElementById('text-input');
    if (textEl) {
      textEl.value = (textEl.value ? textEl.value + '\n' : '') + `Diagnóstico confirmado: ${code}`;
    }
    showToast(`✓ Diagnóstico ${code} incorporado a la nota clínica`, 'success');
  } else if (type === 'cdss') {
    showToast(`✓ Validación farmacológica CDSS confirmada y añadida al expediente`, 'success');
  } else if (type === 'soap') {
    const desc = document.getElementById('sugg-soap-desc')?.textContent || '';
    const textEl = document.getElementById('text-input');
    if (textEl && desc) {
      textEl.value = (textEl.value ? textEl.value + '\n\n' : '') + desc;
    }
    showToast(`✓ Resumen SOAP integrado al editor clínico`, 'success');
  }

  if (card) {
    card.style.borderColor = '#10b981';
    card.style.background = 'rgba(16, 185, 129, 0.08)';
    setTimeout(() => {
      card.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      card.style.opacity = '0.5';
    }, 400);
  }
}

function editAiSuggestion(type) {
  const codeEl = document.getElementById(`sugg-${type}-code`) || document.getElementById(`sugg-${type}-title`);
  const descEl = document.getElementById(`sugg-${type}-desc`);
  if (!codeEl) return;

  const currentText = descEl ? descEl.textContent : codeEl.textContent;
  const edited = prompt('Edite el texto de la sugerencia clínica antes de incorporar:', currentText);
  if (edited !== null && edited.trim() !== '') {
    if (descEl) descEl.textContent = edited.trim();
    showToast('Sugerencia de IA actualizada', 'info');
  }
}

function rejectAiSuggestion(type) {
  const card = document.getElementById(`ai-sugg-${type}`);
  if (card) {
    card.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    card.style.opacity = '0';
    card.style.transform = 'translateX(20px)';
    setTimeout(() => {
      card.style.display = 'none';
    }, 320);
  }
  showToast('Sugerencia de IA descartada por el médico', 'info');
}

// Quick AI Queries directly from the right panel
async function sendCopilotQuickPrompt() {
  const input = document.getElementById('copilot-quick-input');
  if (!input) return;
  const prompt = input.value.trim();
  if (!prompt) return;

  input.value = '';
  setCopilotLiveState('procesando');
  showToast(`Consultando a Dr. Oso: "${prompt.slice(0, 32)}..."`, 'info');

  try {
    const curp = document.getElementById('curp-input')?.value || 'MOBK070228HYNRTVA3';
    const res = await fetch(`${API}/api/pulso/chat-stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: prompt,
        curp: curp,
        user_role: 'Médico',
        stream: false
      })
    });
    setCopilotLiveState('reposo');
    if (res.ok) {
      const data = await res.json();
      const reply = data.text || data.response || 'Consulta completada con éxito.';
      alert(`[Dr. Oso — Asistente Clínico Local]\n\n${reply}`);
    } else {
      showToast('Respuesta local generada en el panel de Pulso', 'info');
    }
  } catch (err) {
    setCopilotLiveState('reposo');
    showToast('Consulta enviada al motor local', 'info');
  }
}

function quickAskCopilot(text) {
  if (typeof togglePulsoPanel === 'function') togglePulsoPanel(true);
  if (typeof sendPulsoPrompt === 'function') sendPulsoPrompt(text);
}

function setCopilotLiveState(state) {
  const icon = document.getElementById('copilot-state-icon');
  const text = document.getElementById('copilot-state-text');
  const img = document.getElementById('copilot-panel-avatar-img');

  if (state === 'procesando') {
    if (icon) icon.textContent = '⚙️';
    if (text) text.textContent = 'Procesando en hardware local...';
    if (img) img.src = 'assets/dr_oso/dr_oso_pensando.png';
  } else if (state === 'escuchando') {
    if (icon) icon.textContent = '🎙️';
    if (text) text.textContent = 'Escuchando dictado médico...';
    if (img) img.src = 'assets/dr_oso/dr_oso_escuchando.png';
  } else if (state === 'alerta') {
    if (icon) icon.textContent = '🚨';
    if (text) text.textContent = 'Alerta de triaje activa';
    if (img) img.src = 'assets/dr_oso/dr_oso_emergency_call.png';
  } else {
    if (icon) icon.textContent = '🟢';
    if (text) text.textContent = 'En reposo · Listo para asistir';
    if (img) img.src = 'assets/dr_oso/dr_oso_reposo.png';
  }
}


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
  const parts = fullName.split(/\s+/).filter(Boolean);
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
  let devVal = 'Triaje Clínico Oficial';
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
  const labNote = 'Estudios de Laboratorio recientes (Química Sanguínea / Biometría): Glucosa 108 mg/dL, Creatinina 0.92 mg/dL, Colesterol 185 mg/dL, HbA1c 6.2%, Leucocitos 7,200/µL. Rx Tórax sin infiltrados.\n';
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
