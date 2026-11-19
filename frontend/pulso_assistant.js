/**
 * pulso_assistant.js — Asistente Híbrido Evolutivo "Dr. Oso · Pulso" (100% IA Local)
 * ====================================================================================
 * - Orquestación híbrida local: LM Studio (Qwen3-8B / MedGemma-4B), Ollama, GGUF o Motor Híbrido.
 * - Ventana deslizante (Sliding Window 8 turnos / 8192 tokens) + Enrutamiento Dinámico.
 * - UI/UX Bio-Clínica sin superposiciones, sin scrollbars dobles y textarea auto-expandible.
 * - Feedback evolutivo inline (👍 / 👎 / ✏️ Corregir y Enseñar) conectado a ChromaDB y DPO JSONL.
 */

const _PulsoState = {
  isOpen: false,
  avatarState: 'reposo', // 'reposo' | 'escuchando' | 'pensando' | 'alerta' | 'contento'
  lmstudioUrl: localStorage.getItem('medicaition_pulso_lmstudio_url') || 'http://localhost:1234/v1',
  ollamaUrl: localStorage.getItem('medicaition_pulso_ollama_url') || 'http://localhost:11434',
  model: localStorage.getItem('medicaition_pulso_model') || 'Qwen3-8B-Q4_K_M',
  ollamaConnected: false,
  lmstudioConnected: false,
  statusLabel: 'Verificando IA Híbrida...',
  availableModels: [],
  messages: [], // Solo en memoria RAM (NOM-024)
  learningStats: { episodic_memories_count: 0, dpo_pairs_count: 0 },
  isStreaming: false,
  isListening: false,
  recognition: null,
  lastSoapStructured: null,
  drag: {
    active: false,
    moved: false,
    startX: 0,
    startY: 0,
    origLeft: null,
    origTop: null,
  },
};

function _pulsoEsc(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

const DR_OSO_ASSETS = {
  reposo: 'assets/dr_oso/dr_oso_reposo.png',
  escuchando: 'assets/dr_oso/dr_oso_escuchando.png',
  pensando: 'assets/dr_oso/dr_oso_pensando.png',
  alerta: 'assets/dr_oso/dr_oso_emergency_call.png',
  contento: 'assets/dr_oso/dr_oso_confirmed.png',
};

if (typeof window !== 'undefined') {
  Object.values(DR_OSO_ASSETS).forEach(src => {
    const img = new Image();
    img.src = src;
  });
}

function PulsoAvatar({ state = 'reposo', size = 110 } = {}) {
  const st = ['reposo', 'escuchando', 'pensando', 'alerta', 'contento'].includes(state)
    ? state
    : 'reposo';
  const imgSrc = DR_OSO_ASSETS[st] || DR_OSO_ASSETS.reposo;
  const isHeaderMode = size <= 56;

  if (isHeaderMode) {
    return `
      <div class="pulso-avatar-stage dr-oso-stage dr-oso-header-portrait state-${st}" style="width:${size}px; height:${size}px;" role="img" aria-label="Dr. Oso - ${st}">
        <img
          src="${imgSrc}"
          class="dr-oso-actual-img dr-oso-header-img"
          alt="Dr. Oso"
          draggable="false"
          loading="eager"
        />
      </div>
    `;
  }

  let overlayHtml = '';
  if (st === 'escuchando') {
    overlayHtml = `
      <div class="dr-oso-listen-waves" aria-hidden="true">
        <span class="dr-oso-wave-ring w1"></span>
        <span class="dr-oso-wave-ring w2"></span>
        <span class="dr-oso-sparkle s1">✨</span>
      </div>
    `;
  } else if (st === 'pensando') {
    overlayHtml = `
      <div class="dr-oso-thought-badge" aria-hidden="true" title="Pensando...">
        <span class="dr-oso-bulb">💡</span>
      </div>
    `;
  } else if (st === 'alerta') {
    overlayHtml = `
      <div class="dr-oso-alert-beacon" aria-hidden="true" title="Alerta clínica">
        <span class="dr-oso-siren">🚨</span>
      </div>
    `;
  } else if (st === 'contento') {
    overlayHtml = `
      <div class="dr-oso-happy-bubble" aria-hidden="true">
        <span class="dr-oso-heart h1">💖</span>
        <span class="dr-oso-heart h2">✨</span>
      </div>
    `;
  }

  return `
    <div class="pulso-avatar-stage dr-oso-stage state-${st}" style="width:${size}px; height:${size}px;" role="img" aria-label="Dr. Oso - Estado ${st}">
      <div class="dr-oso-char-wrap">
        <img
          src="${imgSrc}"
          class="dr-oso-actual-img state-${st}"
          alt="Dr. Oso - Asistente Clínico"
          draggable="false"
          loading="eager"
        />
        <div class="dr-oso-floor-shadow"></div>
      </div>
      ${overlayHtml}
    </div>
  `;
}

window.PulsoAvatar = PulsoAvatar;

function autoResizePulsoInput(el) {
  if (!el) return;
  el.style.height = 'auto';
  const next = Math.min(el.scrollHeight, 110);
  el.style.height = Math.max(40, next) + 'px';
  el.style.overflowY = el.scrollHeight > 110 ? 'auto' : 'hidden';
}
window.autoResizePulsoInput = autoResizePulsoInput;

function triggerPulsoClickReaction() {
  const fab = document.getElementById('pulso-fab-btn');
  if (fab) {
    fab.classList.remove('pulso-clicked-boing');
    void fab.offsetWidth;
    fab.classList.add('pulso-clicked-boing');
    setTimeout(() => fab.classList.remove('pulso-clicked-boing'), 780);
  }
  if (!_PulsoState.isStreaming && !_PulsoState.isListening) {
    setPulsoAvatarState('contento');
    setTimeout(() => {
      if (!_PulsoState.isStreaming && !_PulsoState.isListening) {
        setPulsoAvatarState('reposo');
      }
    }, 1100);
  }
}

function setPulsoAvatarState(newState) {
  _PulsoState.avatarState = newState;
  const fabIcon = document.getElementById('pulso-fab-avatar');
  if (fabIcon) fabIcon.innerHTML = PulsoAvatar({ state: newState, size: 102 });
  const headerIcon = document.getElementById('pulso-header-avatar');
  if (headerIcon) headerIcon.innerHTML = PulsoAvatar({ state: newState, size: 42 });

  document.querySelectorAll('.pulso-state-chip').forEach(btn => {
    const active = btn.dataset.state === newState;
    btn.classList.toggle('active', active);
    btn.classList.toggle('is-active', active);
  });
}

let _lastPulsoToggleTime = 0;

function togglePulsoPanel(forceOpen) {
  const now = Date.now();
  if (typeof forceOpen !== 'boolean' && (now - _lastPulsoToggleTime < 220)) {
    return;
  }
  _lastPulsoToggleTime = now;

  const next = typeof forceOpen === 'boolean' ? forceOpen : !_PulsoState.isOpen;
  _PulsoState.isOpen = next;

  const root = document.getElementById('pulso-floating-root');
  const panel = document.getElementById('pulso-chat-panel');
  const fab = document.getElementById('pulso-fab-btn');
  const bubble = document.getElementById('pulso-greeting-bubble');

  if (root) {
    root.classList.toggle('panel-is-open', next);
  }
  if (panel) {
    panel.classList.toggle('open', next);
    panel.classList.toggle('is-open', next);
    panel.setAttribute('aria-hidden', next ? 'false' : 'true');
    panel.style.display = next ? 'flex' : 'none';
  }
  if (fab) {
    fab.setAttribute('aria-expanded', next ? 'true' : 'false');
  }
  if (bubble && next) {
    bubble.style.display = 'none';
  }

  if (next) {
    checkPulsoLocalAiStatus();
    if (!_PulsoState.messages.length) {
      _appendPulsoWelcomeMessage();
    }
    setTimeout(() => document.getElementById('pulso-chat-input')?.focus(), 80);
  }
}

window.togglePulsoPanel = togglePulsoPanel;

function _appendPulsoWelcomeMessage() {
  _PulsoState.messages.push({
    role: 'assistant',
    isWelcome: true,
    route: 'CLINICAL_NORMATIVE',
    text: (
      'Hola, soy el **Dr. Oso (Pulso)**, tu Copiloto de **IA Híbrida Evolutiva 100% Local** 🩺🐻.\n\n' +
      '- **Ruta Clínica / NOM-004:** RAG Híbrido BM25 + ChromaDB, triaje `scikit-learn` (NEWS2 / qSOFA) y alertas rojas automáticas.\n' +
      '- **Ruta Universal:** Pregúntame sobre programación (Python/SQL/JS), física, matemáticas o redacción sin mezclar datos médicos.\n' +
      '- **Aprendizaje Evolutivo:** Usa `👍`, `👎` o `✏️ Corregir y Enseñar` en cualquier respuesta para adaptarme a tu estilo médico.\n\n' +
      '⚠️ *Revisar siempre las sugerencias diagnósticas o terapéuticas por el médico tratante.*'
    ),
  });
  _renderPulsoMessages();
}

function clearPulsoConversation() {
  _PulsoState.messages = [];
  _PulsoState.lastSoapStructured = null;
  _appendPulsoWelcomeMessage();
  setPulsoAvatarState('reposo');
  const apiBase = typeof API !== 'undefined' ? API : '';
  fetch(`${apiBase}/api/pulso/audit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'PULSO_BORRAR_CONVERSACION', engine: 'local_memory' }),
  }).catch(() => {});
  if (typeof showToast === 'function') {
    showToast('🧹 Conversación de Pulso borrada de la memoria local', 'info');
  }
}

function _updateLearningBadge(stats) {
  if (!stats) return;
  _PulsoState.learningStats = stats;
  const total = (stats.episodic_memories_count || 0) + (stats.dpo_pairs_count || 0);
  const el = document.getElementById('pulso-learning-count');
  if (el) el.textContent = String(total);
  const badge = document.getElementById('pulso-learning-badge');
  if (badge) {
    badge.title = `Memoria episódica: ${stats.episodic_memories_count || 0} | Pares DPO: ${stats.dpo_pairs_count || 0}`;
  }
}

async function checkPulsoLocalAiStatus() {
  const dot = document.getElementById('pulso-conn-dot');
  const lbl = document.getElementById('pulso-conn-label');
  const cfgBadge = document.getElementById('cfg-pulso-status-badge');

  try {
    const apiBase = typeof API !== 'undefined' ? API : '';
    const res = await fetch(
      `${apiBase}/api/pulso/status?ollama_url=${encodeURIComponent(_PulsoState.ollamaUrl)}&lmstudio_url=${encodeURIComponent(_PulsoState.lmstudioUrl)}`
    );
    if (res.ok) {
      const data = await res.json();
      _PulsoState.lmstudioConnected = !!data.lmstudio_connected;
      _PulsoState.ollamaConnected = !!data.ollama_connected;
      _PulsoState.availableModels = data.available_models || [];
      _PulsoState.statusLabel = data.status_label || 'IA Híbrida Evolutiva Activa';
      if (data.learning_stats) _updateLearningBadge(data.learning_stats);
    }
  } catch (_) {
    _PulsoState.statusLabel = 'IA Híbrida Local Offline';
  }

  if (dot) dot.className = 'pulso-conn-dot is-online';
  if (lbl) lbl.textContent = _PulsoState.statusLabel;
  if (cfgBadge) {
    cfgBadge.className = 'pulso-cfg-badge is-online';
    cfgBadge.textContent = _PulsoState.statusLabel;
  }
}

async function saveAndTestPulsoConfig() {
  const urlInp = document.getElementById('cfg-pulso-url');
  const modInp = document.getElementById('cfg-pulso-model');
  const outBox = document.getElementById('cfg-pulso-test-out');

  const url = (urlInp?.value || 'http://localhost:11434').trim().replace(/\/$/, '');
  const model = (modInp?.value || 'Qwen3-8B-Q4_K_M').trim();

  _PulsoState.ollamaUrl = url;
  _PulsoState.model = model;
  try {
    localStorage.setItem('medicaition_pulso_ollama_url', url);
    localStorage.setItem('medicaition_pulso_model', model);
  } catch (_) {}

  if (outBox) {
    outBox.style.display = 'block';
    outBox.textContent = `Probando motores locales (${model})...`;
  }

  try {
    const apiBase = typeof API !== 'undefined' ? API : '';
    const res = await fetch(`${apiBase}/api/pulso/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ollama_url: url, model }),
    });
    const data = await res.json();
    await checkPulsoLocalAiStatus();
    const conn = data.connection || {};
    if (outBox) {
      outBox.innerHTML = conn.lmstudio_connected || conn.ollama_connected
        ? `✅ <strong>Motor neuronal conectado:</strong> ${_pulsoEsc(conn.status_label)}`
        : `ℹ️ <strong>Motor Híbrido Local Integrado activo:</strong> BM25 + ChromaDB CIE-10 + Triaje ML. Para conectar LM Studio en <code>http://localhost:1234/v1</code> carga <code>Qwen3-8B (Q4_K_M)</code>.`;
    }
    if (typeof showToast === 'function') {
      showToast('Configuración de Pulso IA Híbrida guardada', 'success');
    }
  } catch (err) {
    if (outBox) outBox.textContent = 'Error verificando IA local: ' + err.message;
  }
}

function _formatPulsoMarkdown(md) {
  const codeBlocks = [];
  let text = String(md || '');

  // Preservar bloques de código ```lang ... ``` antes de escapar HTML
  text = text.replace(/```([a-zA-Z0-9_-]*)\n([\s\S]*?)```/g, (_, lang, code) => {
    const idx = codeBlocks.length;
    const langTag = lang ? `<span class="pulso-code-lang">${_pulsoEsc(lang)}</span>` : '';
    codeBlocks.push(`<div class="pulso-code-wrap">${langTag}<pre class="pulso-code-block"><code>${_pulsoEsc(code.trimEnd())}</code></pre></div>`);
    return `@@CODEBLOCK_${idx}@@`;
  });

  let safe = _pulsoEsc(text);
  safe = safe.replace(/####\s+(.+)/g, '<div class="pulso-msg-h4">$1</div>');
  safe = safe.replace(/###\s+(.+)/g, '<div class="pulso-msg-h3">$1</div>');
  safe = safe.replace(/^---$/gm, '<hr class="pulso-msg-hr"/>');
  safe = safe.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  safe = safe.replace(/\*([^*\n]+)\*/g, '<em>$1</em>');
  safe = safe.replace(/`([^`\n]+)`/g, '<code class="pulso-inline-code">$1</code>');
  safe = safe.replace(/\[PENDIENTE([^\]]*)\]/g, '<span class="pulso-pending-tag">[PENDIENTE$1]</span>');
  safe = safe.replace(/(⚠️\s*(?:<strong>)?ALERTA CL[IÍ]NICA:?[^<\n]*(?:<\/strong>)?)/gi, '<span class="pulso-alert-inline">$1</span>');
  safe = safe.replace(/\n/g, '<br/>');

  codeBlocks.forEach((html, idx) => {
    safe = safe.replace(`@@CODEBLOCK_${idx}@@`, html);
  });
  return safe;
}

function _buildTelemetryBar(m) {
  const pills = [];
  if (m.route === 'CLINICAL_NORMATIVE') {
    pills.push('<span class="pulso-meta-pill pill-clinical">🩺 Ruta Clínica · RAG BM25+Chroma</span>');
  } else if (m.route === 'AGENTIC_TOOL') {
    pills.push('<span class="pulso-meta-pill pill-agentic">⚙️ Herramienta NOM-004</span>');
  } else if (m.route === 'UNIVERSAL_GENERAL') {
    pills.push('<span class="pulso-meta-pill pill-universal">🌐 Ruta Universal</span>');
  }

  if (m.mlTriage && (m.mlTriage.has_observed_vitals || (m.mlTriage.red_flags && m.mlTriage.red_flags.length))) {
    const lvl = (m.mlTriage.ml_risk_level || 'BAJO').toLowerCase();
    const cls = (lvl.includes('cr') || lvl.includes('alt')) ? 'pill-risk-high' : (lvl.includes('mod') ? 'pill-risk-mod' : 'pill-risk-low');
    pills.push(`<span class="pulso-meta-pill ${cls}">${_pulsoEsc(m.mlTriage.summary_badge)}</span>`);
  }

  if (m.episodicMatches && m.episodicMatches > 0) {
    pills.push(`<span class="pulso-meta-pill pill-episodic">🧬 Estilo médico (${m.episodicMatches})</span>`);
  }

  return pills.length ? `<div class="pulso-msg-telemetry">${pills.join('')}</div>` : '';
}

function _renderPulsoMessages() {
  const container = document.getElementById('pulso-chat-messages');
  if (!container) return;

  container.innerHTML = _PulsoState.messages.map((m, idx) => {
    const isUser = m.role === 'user';
    const isLastStreaming = !isUser && _PulsoState.isStreaming && idx === _PulsoState.messages.length - 1;
    const hasSoap = !isUser && m.soapStructured && idx === _PulsoState.messages.length - 1;

    let contentHtml = '';
    if (isUser) {
      contentHtml = _pulsoEsc(m.text);
    } else if (!m.text && isLastStreaming) {
      contentHtml = '<span class="pulso-typing-indicator"><span class="dot"></span><span class="dot"></span><span class="dot"></span> <em>Dr. Oso está procesando...</em></span>';
    } else {
      contentHtml = _formatPulsoMarkdown(m.text || '');
    }

    const showFeedback = !isUser && !m.isWelcome && !isLastStreaming && m.text;
    const fb = m.feedbackStatus;
    const fbHtml = showFeedback ? `
      <div class="pulso-feedback-bar">
        <button type="button" class="pulso-fb-btn ${fb === 'positive' ? 'is-selected' : ''}" onclick="submitPulsoFeedback(${idx}, 'positive')" title="Marcar respuesta útil (guarda en ChromaDB)">
          👍 Útil
        </button>
        <button type="button" class="pulso-fb-btn ${fb === 'negative' ? 'is-selected-neg' : ''}" onclick="submitPulsoFeedback(${idx}, 'negative')" title="Rechazar respuesta (genera par DPO)">
          👎 Rechazar
        </button>
        <button type="button" class="pulso-fb-btn ${fb === 'corrected' ? 'is-selected' : ''}" onclick="togglePulsoCorrectionEditor(${idx})" title="Editar respuesta y enseñar al modelo">
          ✏️ Corregir y Enseñar
        </button>
      </div>
      ${m.editorOpen ? `
        <div class="pulso-correction-box">
          <div class="pulso-correction-label">Edita la respuesta ideal para que Dr. Oso aprenda tu criterio clínico (ChromaDB + DPO):</div>
          <textarea id="pulso-corr-text-${idx}" class="pulso-correction-textarea" rows="4">${_pulsoEsc(m.text)}</textarea>
          <div class="pulso-correction-actions">
            <button type="button" class="pulso-corr-cancel" onclick="togglePulsoCorrectionEditor(${idx})">Cancelar</button>
            <button type="button" class="pulso-corr-save" onclick="submitPulsoCorrection(${idx})">💾 Guardar y Enseñar</button>
          </div>
        </div>
      ` : ''}
    ` : '';

    return `
      <div class="pulso-msg ${isUser ? 'pulso-msg-user' : 'pulso-msg-assistant'}">
        ${!isUser ? _buildTelemetryBar(m) : ''}
        <div class="pulso-msg-bubble">${contentHtml}</div>
        ${hasSoap ? `
          <button type="button" class="pulso-apply-soap-btn" onclick="applyPulsoSoapToExpediente()">
            📋 Pasar borrador SOAP al Expediente Activo
          </button>
        ` : ''}
        ${fbHtml}
      </div>
    `;
  }).join('');

  container.scrollTop = container.scrollHeight;
}

function togglePulsoCorrectionEditor(msgIdx) {
  const m = _PulsoState.messages[msgIdx];
  if (!m) return;
  m.editorOpen = !m.editorOpen;
  _renderPulsoMessages();
  if (m.editorOpen) {
    setTimeout(() => document.getElementById(`pulso-corr-text-${msgIdx}`)?.focus(), 40);
  }
}
window.togglePulsoCorrectionEditor = togglePulsoCorrectionEditor;

async function submitPulsoFeedback(msgIdx, rating) {
  const m = _PulsoState.messages[msgIdx];
  if (!m) return;
  const activeCurp = (typeof _ExpCareState !== 'undefined' && _ExpCareState.curp)
    || (window.AppState && window.AppState.selectedPatientCurp)
    || document.getElementById('curp-input')?.value?.trim()
    || '';
  const apiBase = typeof API !== 'undefined' ? API : '';

  try {
    const res = await fetch(`${apiBase}/api/pulso/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: m.prompt || '',
        original_response: m.text || '',
        rating,
        curp: activeCurp,
        intent: m.route || 'CLINICAL_NORMATIVE',
      }),
    });
    if (res.ok) {
      const data = await res.json();
      m.feedbackStatus = rating;
      if (data.stats) _updateLearningBadge(data.stats);
      _renderPulsoMessages();
      if (typeof showToast === 'function') {
        showToast(
          rating === 'positive'
            ? '👍 Preferencia guardada en Memoria Evolutiva (ChromaDB)'
            : '👎 Rechazo registrado en training_data/dpo_pairs.jsonl',
          rating === 'positive' ? 'success' : 'info'
        );
      }
    }
  } catch (err) {
    console.error('[PulsoFeedback] Error:', err);
  }
}
window.submitPulsoFeedback = submitPulsoFeedback;

async function submitPulsoCorrection(msgIdx) {
  const m = _PulsoState.messages[msgIdx];
  const ta = document.getElementById(`pulso-corr-text-${msgIdx}`);
  if (!m || !ta) return;

  const corrected = ta.value.trim();
  if (!corrected) return;

  const activeCurp = (typeof _ExpCareState !== 'undefined' && _ExpCareState.curp)
    || (window.AppState && window.AppState.selectedPatientCurp)
    || document.getElementById('curp-input')?.value?.trim()
    || '';
  const apiBase = typeof API !== 'undefined' ? API : '';

  try {
    const res = await fetch(`${apiBase}/api/pulso/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt: m.prompt || '',
        original_response: m.text || '',
        corrected_response: corrected,
        rating: 'corrected',
        curp: activeCurp,
        intent: m.route || 'CLINICAL_NORMATIVE',
      }),
    });
    if (res.ok) {
      const data = await res.json();
      m.text = corrected;
      m.feedbackStatus = 'corrected';
      m.editorOpen = false;
      if (data.stats) _updateLearningBadge(data.stats);
      _renderPulsoMessages();
      if (typeof showToast === 'function') {
        showToast('🧬 Corrección aprendida en ChromaDB (episodic_learning) y DPO JSONL', 'success');
      }
    }
  } catch (err) {
    console.error('[PulsoCorrection] Error:', err);
  }
}
window.submitPulsoCorrection = submitPulsoCorrection;

function applyPulsoSoapToExpediente() {
  const soap = _PulsoState.lastSoapStructured;
  if (!soap) return;
  if (typeof _ExpCareState !== 'undefined') {
    _ExpCareState.soap = {
      s: soap.s || _ExpCareState.soap.s,
      o: soap.o || _ExpCareState.soap.o,
      a: soap.a || _ExpCareState.soap.a,
      p: soap.p || _ExpCareState.soap.p,
    };
    if (typeof switchMainTab === 'function') switchMainTab('expediente');
    if (typeof _renderExpSoap === 'function') _renderExpSoap();
    if (typeof showToast === 'function') {
      showToast('✅ Borrador SOAP aplicado en Atención Especializada (Revisar por el médico)', 'success');
    }
  }
}

async function sendPulsoPrompt(presetText) {
  const input = document.getElementById('pulso-chat-input');
  const sendBtn = document.getElementById('pulso-send-btn');
  const prompt = (presetText != null ? presetText : (input?.value || '')).trim();

  if (_PulsoState.isStreaming || !prompt) return;

  if (presetText == null && input) {
    input.value = '';
    autoResizePulsoInput(input);
  }

  // Sliding Window: construir historial de últimos 8 turnos antes de agregar el nuevo
  const historyWindow = _PulsoState.messages
    .filter(m => !m.isWelcome && m.text && m.text.trim())
    .slice(-8)
    .map(m => ({ role: m.role, content: m.text }));

  _PulsoState.messages.push({ role: 'user', text: prompt });
  _PulsoState.messages.push({
    role: 'assistant',
    prompt,
    text: '',
    route: null,
    mlTriage: null,
    ragSources: [],
    episodicMatches: 0,
    feedbackStatus: null,
    editorOpen: false,
  });
  const botIdx = _PulsoState.messages.length - 1;
  _PulsoState.isStreaming = true;
  setPulsoAvatarState('pensando');
  _renderPulsoMessages();

  if (input) input.disabled = true;
  if (sendBtn) sendBtn.disabled = true;

  const activeCurp = (typeof _ExpCareState !== 'undefined' && _ExpCareState.curp)
    || (window.AppState && window.AppState.selectedPatientCurp)
    || document.getElementById('curp-input')?.value?.trim()
    || '';

  const apiBase = (typeof API !== 'undefined' && API != null) ? API : (window.API || '');

  try {
    const res = await fetch(`${apiBase}/api/pulso/chat-stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt,
        curp: activeCurp,
        history: historyWindow,
        lmstudio_url: _PulsoState.lmstudioUrl,
        ollama_url: _PulsoState.ollamaUrl,
        model: _PulsoState.model,
      }),
    });

    if (!res.ok || !res.body) {
      throw new Error(`Error HTTP ${res.status}`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';
    let finalState = 'reposo';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const evt = JSON.parse(line);
          if (evt.type === 'meta') {
            finalState = evt.avatar_state || 'reposo';
            _PulsoState.messages[botIdx].route = evt.route || 'CLINICAL_NORMATIVE';
            _PulsoState.messages[botIdx].mlTriage = evt.ml_triage || null;
            _PulsoState.messages[botIdx].ragSources = evt.rag_sources || [];
            _PulsoState.messages[botIdx].episodicMatches = evt.episodic_matches || 0;
            if (evt.learning_stats) _updateLearningBadge(evt.learning_stats);
            if (evt.soap_structured) {
              _PulsoState.lastSoapStructured = evt.soap_structured;
              _PulsoState.messages[botIdx].soapStructured = evt.soap_structured;
            }
          } else if (evt.type === 'token' && evt.content) {
            _PulsoState.messages[botIdx].text += evt.content;
            _renderPulsoMessages();
          }
        } catch (eJson) {
          console.warn('[PulsoDebug] NDJSON parse warning:', line, eJson);
        }
      }
    }

    setPulsoAvatarState(finalState);
  } catch (err) {
    console.error('[PulsoDebug] Error:', err);
    _PulsoState.messages[botIdx].text =
      `⚠️ Error comunicando con el orquestador local: ${err.message}. Verifica que el backend esté activo en http://127.0.0.1:8000.`;
    setPulsoAvatarState('alerta');
  } finally {
    _PulsoState.isStreaming = false;
    if (input) {
      input.disabled = false;
      input.focus();
    }
    if (sendBtn) sendBtn.disabled = false;
    _renderPulsoMessages();
  }
}

function runPulsoQuickAction(kind) {
  if (kind === 'transfer') {
    sendPulsoPrompt('Genera el resumen de transferencia interhospitalaria y el análisis de divergencia de protocolos para el paciente actual.');
  } else if (kind === 'summary') {
    sendPulsoPrompt('Dame el resumen previo del paciente actual con sus alergias, signos vitales y últimas consultas.');
  } else if (kind === 'triage') {
    sendPulsoPrompt('Evalúa el riesgo clínico ML (NEWS2, qSOFA y signos de alarma) del paciente activo actual.');
  } else if (kind === 'soap') {
    const input = document.getElementById('pulso-chat-input');
    const typed = input?.value?.trim();
    if (typed) {
      input.value = '';
      autoResizePulsoInput(input);
      sendPulsoPrompt(`Genera borrador de nota SOAP para: ${typed}`);
    } else {
      sendPulsoPrompt('Genera un borrador de nota SOAP para paciente con dolor abdominal de 2 días en epigastrio, fiebre 37.8 C, FC 82, TA 128/82.');
    }
  } else if (kind === 'search') {
    sendPulsoPrompt('Busca los pacientes registrados y las citas programadas en la agenda.');
  } else if (kind === 'infarto') {
    sendPulsoPrompt('¿Cuál es el protocolo de Código Infarto ante sospecha de IAMCEST en urgencias? Detalla tiempos puerta-balón, DAPT y contraindicaciones de nitratos.');
  } else if (kind === 'dengue') {
    sendPulsoPrompt('¿Cuáles son los signos de alarma en Dengue según la OMS/OPS y qué plan de reanimación hídrica se indica?');
  } else if (kind === 'pediatrico') {
    sendPulsoPrompt('¿Cuál es el cálculo de dosis de paracetamol e ibuprofeno en mg/kg/día para un paciente pediátrico de 12 kg con fiebre?');
  } else if (kind === 'tfg') {
    sendPulsoPrompt('¿Cómo calculo la Tasa de Filtrado Glomerular con Cockcroft-Gault y cuándo debo ajustar fármacos nefrotóxicos?');
  }
}

function togglePulsoMicDictation() {
  const micBtn = document.getElementById('pulso-mic-btn');
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (_PulsoState.isListening && _PulsoState.recognition) {
    _PulsoState.recognition.stop();
    _PulsoState.isListening = false;
    setPulsoAvatarState('reposo');
    micBtn?.classList.remove('listening');
    return;
  }

  if (!SpeechRec) {
    if (typeof showToast === 'function') {
      showToast('Este navegador no soporta dictado por voz directo; escribe tu dictado en la caja de texto.', 'info');
    }
    document.getElementById('pulso-chat-input')?.focus();
    return;
  }

  const rec = new SpeechRec();
  rec.lang = 'es-MX';
  rec.continuous = false;
  rec.interimResults = false;

  rec.onstart = () => {
    _PulsoState.isListening = true;
    setPulsoAvatarState('escuchando');
    micBtn?.classList.add('listening');
  };

  rec.onresult = (ev) => {
    const transcript = Array.from(ev.results).map(r => r[0].transcript).join(' ').trim();
    const input = document.getElementById('pulso-chat-input');
    if (input && transcript) {
      input.value = (input.value ? input.value + ' ' : '') + transcript;
      autoResizePulsoInput(input);
      input.focus();
    }
  };

  rec.onend = () => {
    _PulsoState.isListening = false;
    micBtn?.classList.remove('listening');
    if (!_PulsoState.isStreaming) setPulsoAvatarState('reposo');
  };

  rec.onerror = () => {
    _PulsoState.isListening = false;
    micBtn?.classList.remove('listening');
    setPulsoAvatarState('reposo');
  };

  _PulsoState.recognition = rec;
  rec.start();
}

function resetPulsoToCorner() {
  const root = document.getElementById('pulso-floating-root');
  if (!root) return;
  root.style.left = 'auto';
  root.style.top = 'auto';
  root.style.right = '24px';
  root.style.bottom = '44px';
  root.classList.remove('pulso-left-side');
  setPulsoAvatarState('contento');
  setTimeout(() => {
    if (!_PulsoState.isStreaming && !_PulsoState.isListening) {
      setPulsoAvatarState('reposo');
    }
  }, 1500);
}

function _initPulsoDraggable() {
  const fab = document.getElementById('pulso-fab-btn');
  const header = document.querySelector('.pulso-chat-header');
  const root = document.getElementById('pulso-floating-root');
  if (!fab || !root) return;

  let isDragging = false;
  let didMove = false;
  let startX = 0, startY = 0;
  let origLeft = 0, origTop = 0;
  let justDragged = false;

  const onPointerDown = (e, isFab) => {
    if (e.button !== undefined && e.button !== 0) return;
    if (!isFab && e.target.closest('button')) return;
    isDragging = true;
    didMove = false;
    startX = e.clientX;
    startY = e.clientY;
    const rect = root.getBoundingClientRect();
    origLeft = rect.left;
    origTop = rect.top;
    window.addEventListener('pointermove', onPointerMove, { passive: false });
    window.addEventListener('pointerup', onPointerUp, { passive: false });
    window.addEventListener('pointercancel', onPointerUp, { passive: false });
  };

  const onPointerMove = (e) => {
    if (!isDragging) return;
    const dx = e.clientX - startX;
    const dy = e.clientY - startY;
    if (!didMove && Math.hypot(dx, dy) > 5) {
      didMove = true;
      document.body.style.userSelect = 'none';
      if (fab) fab.style.cursor = 'grabbing';
    }
    if (!didMove) return;
    e.preventDefault();
    const rootRect = root.getBoundingClientRect();
    const maxLeft = Math.max(10, window.innerWidth - (rootRect.width || 120) - 10);
    const maxTop = Math.max(10, window.innerHeight - (rootRect.height || 120) - 10);
    const newLeft = Math.min(maxLeft, Math.max(10, origLeft + dx));
    const newTop = Math.min(maxTop, Math.max(10, origTop + dy));
    root.style.right = 'auto';
    root.style.bottom = 'auto';
    root.style.left = `${Math.round(newLeft)}px`;
    root.style.top = `${Math.round(newTop)}px`;
    root.classList.toggle('pulso-left-side', newLeft < 400);
  };

  const onPointerUp = () => {
    if (!isDragging) return;
    isDragging = false;
    document.body.style.userSelect = '';
    if (fab) fab.style.cursor = 'pointer';
    window.removeEventListener('pointermove', onPointerMove);
    window.removeEventListener('pointerup', onPointerUp);
    window.removeEventListener('pointercancel', onPointerUp);
    if (didMove) {
      justDragged = true;
      setTimeout(() => { justDragged = false; }, 250);
    }
  };

  fab.onpointerdown = (e) => onPointerDown(e, true);
  if (header) header.onpointerdown = (e) => onPointerDown(e, false);

  fab.onclick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (justDragged || didMove) return;
    triggerPulsoClickReaction();
    togglePulsoPanel();
  };
}

function initPulsoAssistant() {
  const fabAvatar = document.getElementById('pulso-fab-avatar');
  if (fabAvatar) {
    fabAvatar.innerHTML = PulsoAvatar({ state: _PulsoState.avatarState || 'reposo', size: 102 });
  }
  const headerAvatar = document.getElementById('pulso-header-avatar');
  if (headerAvatar) {
    headerAvatar.innerHTML = PulsoAvatar({ state: _PulsoState.avatarState || 'reposo', size: 42 });
  }

  const urlInp = document.getElementById('cfg-pulso-url');
  if (urlInp) urlInp.value = _PulsoState.ollamaUrl;
  const modInp = document.getElementById('cfg-pulso-model');
  if (modInp) modInp.value = _PulsoState.model;

  _initPulsoDraggable();
  checkPulsoLocalAiStatus();

  window.removeEventListener('keydown', _handlePulsoGlobalKey);
  window.addEventListener('keydown', _handlePulsoGlobalKey);
}

function _handlePulsoGlobalKey(e) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'j') {
    e.preventDefault();
    togglePulsoPanel();
  } else if (e.key === 'Escape' && _PulsoState.isOpen) {
    togglePulsoPanel(false);
  }
}

window.initPulsoAssistant = initPulsoAssistant;
window.togglePulsoPanel = togglePulsoPanel;
window.resetPulsoToCorner = resetPulsoToCorner;
window.sendPulsoPrompt = sendPulsoPrompt;
window.runPulsoQuickAction = runPulsoQuickAction;
window.clearPulsoConversation = clearPulsoConversation;
window.togglePulsoMicDictation = togglePulsoMicDictation;
window.setPulsoAvatarState = setPulsoAvatarState;
window.applyPulsoSoapToExpediente = applyPulsoSoapToExpediente;
window._PulsoState = _PulsoState;

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initPulsoAssistant);
} else {
  initPulsoAssistant();
}
window.addEventListener('load', initPulsoAssistant);
