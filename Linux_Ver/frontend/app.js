/* global state */
let currentMode = 'audio';
let currentResultTab = 'datos';
let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let timerInterval = null;
let timerSeconds = 0;
let recordedBlob = null;
let lastProcessedCurp = null;

const API = '';  // same origin

/* ── MODE TOGGLE ── */
function setMode(mode) {
  currentMode = mode;
  document.getElementById('btn-audio').classList.toggle('active', mode === 'audio');
  document.getElementById('btn-text').classList.toggle('active', mode === 'text');
  document.getElementById('audio-panel').style.display = mode === 'audio' ? 'block' : 'none';
  document.getElementById('text-panel').style.display  = mode === 'text'  ? 'block' : 'none';
}

/* ── RESULTS TAB TOGGLE ── */
function setResultTab(tab) {
  currentResultTab = tab;
  document.getElementById('tab-datos').classList.toggle('active', tab === 'datos');
  document.getElementById('tab-nota').classList.toggle('active', tab === 'nota');
  document.getElementById('results-content').style.display = tab === 'datos' ? 'flex' : 'none';
  document.getElementById('results-content').style.flexDirection = tab === 'datos' ? 'column' : '';
  document.getElementById('results-content').style.gap = tab === 'datos' ? '16px' : '';
  document.getElementById('nota-content').style.display = tab === 'nota' ? 'block' : 'none';

  // Load the nota médica iframe when switching to that tab
  if (tab === 'nota' && lastProcessedCurp) {
    loadNotaMedica(lastProcessedCurp);
  }
}

/* ── NOTA MÉDICA ── */
function loadNotaMedica(curp) {
  const iframe = document.getElementById('nota-iframe');
  const url = `${API}/api/input/nota-medica/${encodeURIComponent(curp)}`;
  if (iframe.src !== url && iframe.getAttribute('data-loaded-curp') !== curp) {
    iframe.src = url;
    iframe.setAttribute('data-loaded-curp', curp);
  }
}

function printNotaMedica() {
  if (!lastProcessedCurp) {
    showToast('Procesa un expediente primero', 'error');
    return;
  }
  const url = `${API}/api/input/nota-medica/${encodeURIComponent(lastProcessedCurp)}`;
  const printWindow = window.open(url, '_blank', 'width=900,height=700');
  if (printWindow) {
    printWindow.addEventListener('load', () => {
      setTimeout(() => printWindow.print(), 500);
    });
  }
}

/* ── RECORDER ── */
async function toggleRecord() {
  if (!isRecording) await startRecording();
  else stopRecording();
}

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];
    recordedBlob = null;

    mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
    mediaRecorder.onstop = () => {
      recordedBlob = new Blob(audioChunks, { type: 'audio/webm' });
      const url = URL.createObjectURL(recordedBlob);
      const playback = document.getElementById('audio-playback');
      playback.src = url;
      document.getElementById('audio-preview').style.display = 'block';
    };

    mediaRecorder.start();
    isRecording = true;

    document.getElementById('record-btn').classList.add('recording');
    document.getElementById('record-label').textContent = 'Grabando...';
    document.getElementById('record-icon').innerHTML = `
      <svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor">
        <rect x="6" y="6" width="12" height="12" rx="2"/>
      </svg>`;
    document.getElementById('record-timer').style.display = 'block';
    document.getElementById('wave-bars').classList.add('active');

    timerSeconds = 0;
    timerInterval = setInterval(() => {
      timerSeconds++;
      const m = String(Math.floor(timerSeconds / 60)).padStart(2, '0');
      const s = String(timerSeconds % 60).padStart(2, '0');
      document.getElementById('record-timer').textContent = `${m}:${s}`;
    }, 1000);

  } catch (err) {
    showToast('Error al acceder al micrófono: ' + err.message, 'error');
  }
}

function stopRecording() {
  if (mediaRecorder && isRecording) {
    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach(t => t.stop());
    isRecording = false;
    clearInterval(timerInterval);

    document.getElementById('record-btn').classList.remove('recording');
    document.getElementById('record-label').textContent = 'Audio capturado ✓';
    document.getElementById('record-icon').innerHTML = `
      <svg width="28" height="28" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="8"/></svg>`;
    document.getElementById('wave-bars').classList.remove('active');
  }
}

/* ── SUBMIT ── */
async function submitData() {
  const curp  = document.getElementById('curp-input').value.trim();
  const clues = document.getElementById('clues-input').value.trim();

  if (currentMode === 'audio' && !recordedBlob)
    return showToast('Graba un audio primero', 'error');
  if (currentMode === 'text' && !document.getElementById('text-input').value.trim())
    return showToast('Escribe el texto clínico', 'error');

  setLoading(true);

  try {
    let data;
    if (currentMode === 'audio') {
      const fd = new FormData();
      fd.append('audio', recordedBlob, 'audio.webm');
      fd.append('curp', curp);
      fd.append('clues', clues);
      const res = await fetch(`${API}/api/input/audio`, { method: 'POST', body: fd });
      if (!res.ok) throw new Error(await res.text());
      data = await res.json();
    } else {
      const fd = new FormData();
      fd.append('text', document.getElementById('text-input').value.trim());
      fd.append('curp', curp);
      fd.append('clues', clues);
      const res = await fetch(`${API}/api/input/text`, { method: 'POST', body: fd });
      if (!res.ok) throw new Error(await res.text());
      data = await res.json();
    }

    lastProcessedCurp = data.curp || curp;
    renderResults(data);
    loadPatients();
    showToast('Expediente procesado y guardado', 'success');

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
  document.getElementById('results-content').style.display = 'flex';
  document.getElementById('results-content').style.flexDirection = 'column';
  document.getElementById('results-content').style.gap = '16px';

  // Reset to datos tab
  setResultTab('datos');

  // Reset iframe for fresh load
  const iframe = document.getElementById('nota-iframe');
  iframe.removeAttribute('data-loaded-curp');
  iframe.src = 'about:blank';

  // Texto original
  document.getElementById('result-text').textContent = data.texto_original || '—';

  // Demograficos
  const demo = data.datos_demograficos || {};
  const demoEl = document.getElementById('result-demo');
  demoEl.innerHTML = '';
  const demoFields = { nombre: 'Nombre', edad: 'Edad', sexo: 'Sexo', curp: 'CURP' };
  Object.entries(demoFields).forEach(([k, label]) => {
    if (demo[k]) {
      demoEl.innerHTML += `<span class="tag tag-demo">${label}: ${demo[k]}</span>`;
    }
  });
  if (!demoEl.innerHTML) demoEl.innerHTML = '<span style="font-size:12px;color:var(--text-muted)">Sin datos demográficos detectados</span>';

  // CIE-10
  const cie10El = document.getElementById('result-cie10');
  cie10El.innerHTML = '';
  const categories = {
    sintomas_referidos:       { label: 'Síntomas Referidos (CIE-10)',       cls: 'tag-sint' },
    diagnosticos_tentativos:  { label: 'Diagnósticos Tentativos (CIE-10)',  cls: 'tag-padc' },
    tratamientos:             { label: 'Procedimientos (CIE-9MC)',          cls: 'tag-trat' },
  };

  const codes = data.codigos_cie10 || {};
  Object.entries(categories).forEach(([key, { label }]) => {
    const items = codes[key] || [];
    if (!items.length) return;

    let html = `<div class="cie10-category"><div class="cie10-label">${label}</div>`;
    items.forEach(item => {
      const sim = item.similitud || 0;
      const simCls = sim >= 0.75 ? 'sim-high' : sim >= 0.5 ? 'sim-mid' : 'sim-low';
      const code = item.codigo || '—';
      html += `
        <div class="cie10-item">
          <span class="cie10-code">${code}</span>
          <div class="cie10-info">
            <span class="cie10-desc">${item.descripcion || item.termino_original}</span>
            <span class="cie10-original">Término: "${item.termino_original}"</span>
          </div>
          <span class="sim-badge ${simCls}">${Math.round(sim * 100)}%</span>
        </div>`;
    });
    html += '</div>';
    cie10El.innerHTML += html;
  });

  if (!cie10El.innerHTML) {
    cie10El.innerHTML = '<span style="font-size:12px;color:var(--text-muted)">Sin entidades mapeadas</span>';
  }

  // JSON completo (exclude nota_medica_html from display to keep it clean)
  const displayData = { ...data };
  delete displayData.nota_medica_html;
  document.getElementById('result-json').textContent = JSON.stringify(displayData, null, 2);
}

/* ── PATIENTS ── */
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

function renderPatients(patients) {
  const el = document.getElementById('patients-list');
  if (!patients.length) {
    el.innerHTML = '<div class="no-patients">Sin expedientes registrados</div>';
    return;
  }
  el.innerHTML = patients.map(p => `
    <div class="patient-card" onclick="loadPatient('${esc(p.curp)}')">
      <span class="patient-curp">${esc(p.curp)}</span>
      <span class="patient-name">${esc(p.nombre) || 'Nombre no registrado'}</span>
      <span class="patient-meta">${esc(p.clues_institucion)} · ${formatDate(p.timestamp)}${p.num_notas > 1 ? ` · ${p.num_notas} notas` : ''}</span>
    </div>
  `).join('');
}

async function loadPatient(curp) {
  try {
    const res = await fetch(`${API}/api/patients/${curp}`);
    if (!res.ok) return showToast('Paciente no encontrado', 'error');
    const data = await res.json();
    lastProcessedCurp = curp;
    renderResults(data);
    window.scrollTo({ top: 0, behavior: 'smooth' });
  } catch (err) {
    showToast('Error al cargar expediente', 'error');
  }
}

function searchPatient() {
  const q = document.getElementById('search-input').value.trim().toUpperCase();
  const cards = document.querySelectorAll('.patient-card');
  cards.forEach(c => {
    const curp = c.querySelector('.patient-curp')?.textContent || '';
    c.style.display = curp.includes(q) ? 'flex' : 'none';
  });
}

/* ── SANITIZE ── */
function esc(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

/* ── UTILS ── */
function setLoading(on) {
  const btn = document.getElementById('submit-btn');
  btn.disabled = on;
  document.getElementById('submit-label').style.display = on ? 'none' : 'inline';
  document.getElementById('spinner').style.display = on ? 'block' : 'none';
  document.getElementById('status-text').textContent = on ? 'Procesando...' : 'Sistema listo';
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

/* ── INIT ── */
document.addEventListener('DOMContentLoaded', () => {
  loadPatients();
});

