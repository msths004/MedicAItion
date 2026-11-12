/**
 * pulso_assistant.js — Asistente Clínico con Avatar "Pulso" (100% IA Local)
 * =========================================================================
 * - Componente SVG inline <PulsoAvatar /> con estados:
 *     "reposo", "escuchando", "pensando", "alerta", "contento"
 * - Arrastrable libremente por toda la pantalla (drag & drop con límites de viewport)
 *   + botón "Volver a la esquina".
 * - Panel de chat accesible de 360 px + atajo Ctrl/Cmd+J + micrófono (dictado es-MX).
 * - Cliente de IA Local con streaming compatible con Ollama (http://localhost:11434)
 *   y Motor Clínico Local integrado (/api/pulso/chat-stream) sin enviar datos al exterior.
 * - Reglas clínicas estrictas: no inventar datos, marcar [PENDIENTE] y aviso
 *   "Revisar por el médico".
 * - Privacidad: conversación solo en memoria RAM, botón "Borrar conversación" y
 *   registro en bitácora NOM-024 sin contenido sensible.
 */

const _PulsoState = {
  isOpen: false,
  avatarState: 'reposo', // 'reposo' | 'escuchando' | 'pensando' | 'alerta' | 'contento'
  ollamaUrl: localStorage.getItem('medicaition_pulso_ollama_url') || 'http://localhost:11434',
  model: localStorage.getItem('medicaition_pulso_model') || 'qwen2.5:7b-instruct',
  ollamaConnected: false,
  statusLabel: 'Verificando IA local...',
  availableModels: [],
  messages: [], // Solo en memoria RAM (nunca en localStorage por privacidad)
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

/**
 * Renderiza el SVG inline del componente <PulsoAvatar /> fiel al diseño:
 * Robot cápsula turquesa (#14B8A6, borde #0F766E), visor oscuro (#0F172A),
 * ojos #5EEAD3, antena con punto ámbar (#F59E0B), chip y línea de pulso en el pecho.
 */
function PulsoAvatar({ state = 'reposo', size = 84 } = {}) {
  const st = ['reposo', 'escuchando', 'pensando', 'alerta', 'contento'].includes(state)
    ? state
    : 'reposo';

  const isAlert = st === 'alerta';
  const isThinking = st === 'pensando';
  const isListening = st === 'escuchando';
  const isHappy = st === 'contento';

  const eyeColor = isAlert ? '#F59E0B' : '#5EEAD3';

  let visorContent = '';
  if (isThinking) {
    visorContent = `
      <g class="pulso-thinking-dots" fill="#5EEAD3">
        <circle class="pulso-dot d1" cx="47" cy="48" r="3.6" />
        <circle class="pulso-dot d2" cx="60" cy="48" r="3.6" />
        <circle class="pulso-dot d3" cx="73" cy="48" r="3.6" />
      </g>
    `;
  } else {
    visorContent = `
      <g class="pulso-eyes ${st === 'reposo' ? 'can-blink' : ''}">
        <ellipse cx="47" cy="46" rx="6.2" ry="7.4" fill="${eyeColor}" />
        <ellipse cx="73" cy="46" rx="6.2" ry="7.4" fill="${eyeColor}" />
        ${!isAlert ? `
          <circle cx="45" cy="43.5" r="2.1" fill="#FFFFFF" />
          <circle cx="71" cy="43.5" r="2.1" fill="#FFFFFF" />
        ` : ''}
      </g>
      ${isHappy ? `
        <ellipse cx="38" cy="53" rx="3.8" ry="2" fill="#F472B6" opacity="0.85" />
        <ellipse cx="82" cy="53" rx="3.8" ry="2" fill="#F472B6" opacity="0.85" />
      ` : ''}
      ${isAlert
        ? `<line x1="52" y1="57" x2="68" y2="57" stroke="#F59E0B" stroke-width="3" stroke-linecap="round" />`
        : `<path d="M 52 55 Q 60 61.5 68 55" fill="none" stroke="#5EEAD3" stroke-width="2.8" stroke-linecap="round" />`
      }
    `;
  }

  const soundWaves = isListening ? `
    <g class="pulso-sound-waves" fill="none" stroke="#0F766E" stroke-width="2.4" stroke-linecap="round">
      <path class="wave w1" d="M 103 38 Q 109 46 103 54" />
      <path class="wave w2" d="M 109 33 Q 117 46 109 59" />
      <path class="wave w1" d="M 17 38 Q 11 46 17 54" />
    </g>
  ` : '';

  return `
    <svg class="pulso-avatar-svg state-${st}" width="${size}" height="${size}" viewBox="0 0 120 132" role="img" aria-label="Avatar de Pulso en estado ${st}">
      <!-- Sombra inferior -->
      <ellipse cx="60" cy="124" rx="30" ry="4.5" fill="#CBD5E1" opacity="0.65" />

      <!-- Antena con punto ámbar (#F59E0B) -->
      <line x1="60" y1="12" x2="60" y2="24" stroke="#0F766E" stroke-width="3" stroke-linecap="round" />
      <circle class="pulso-antenna-tip" cx="60" cy="9" r="5.5" fill="#F59E0B" stroke="#0F766E" stroke-width="2" />

      <!-- Orejas laterales -->
      <circle cx="24" cy="46" r="6" fill="#0F766E" />
      <circle cx="96" cy="46" r="6" fill="#0F766E" />

      <!-- Cabeza cápsula turquesa (#14B8A6, borde #0F766E) -->
      <rect x="26" y="23" width="68" height="46" rx="22" fill="#14B8A6" stroke="#0F766E" stroke-width="2.6" />

      <!-- Visor oscuro (#0F172A) -->
      <rect x="33" y="30" width="54" height="32" rx="15" fill="#0F172A" />

      ${visorContent}
      ${soundWaves}

      <!-- Brazos cápsula -->
      <rect class="pulso-arm-left" x="22" y="75" width="12" height="27" rx="6" fill="#14B8A6" stroke="#0F766E" stroke-width="2.4" />
      <g class="pulso-arm-right" transform="rotate(-24 92 80)">
        <rect x="86" y="74" width="12" height="27" rx="6" fill="#14B8A6" stroke="#0F766E" stroke-width="2.4" />
      </g>

      <!-- Pies -->
      <ellipse cx="49" cy="117" rx="11" ry="5.5" fill="#0F766E" />
      <ellipse cx="71" cy="117" rx="11" ry="5.5" fill="#0F766E" />

      <!-- Torso cápsula turquesa -->
      <rect x="35" y="71" width="50" height="43" rx="20" fill="#14B8A6" stroke="#0F766E" stroke-width="2.6" />

      <!-- Ventana de pecho con línea de pulso y chip -->
      <rect x="44" y="77" width="32" height="30" rx="8" fill="#CCFBF1" />
      <!-- Línea ECG de pulso -->
      <polyline points="47,84 53,84 56,79 59,89 62,84 73,84" fill="none" stroke="#0F766E" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
      <!-- Chip en el pecho -->
      <rect x="53" y="90" width="14" height="13" rx="2.5" fill="none" stroke="#0F766E" stroke-width="1.8" />
      <rect x="56.5" y="93.5" width="7" height="6" rx="1" fill="#0F766E" />
      <line x1="56" y1="88" x2="56" y2="90" stroke="#0F766E" stroke-width="1.5" />
      <line x1="60" y1="88" x2="60" y2="90" stroke="#0F766E" stroke-width="1.5" />
      <line x1="64" y1="88" x2="64" y2="90" stroke="#0F766E" stroke-width="1.5" />
      <line x1="56" y1="103" x2="56" y2="105" stroke="#0F766E" stroke-width="1.5" />
      <line x1="60" y1="103" x2="60" y2="105" stroke="#0F766E" stroke-width="1.5" />
      <line x1="64" y1="103" x2="64" y2="105" stroke="#0F766E" stroke-width="1.5" />
    </svg>
  `;
}

window.PulsoAvatar = PulsoAvatar;

function setPulsoAvatarState(newState) {
  _PulsoState.avatarState = newState;
  const fabIcon = document.getElementById('pulso-fab-avatar');
  if (fabIcon) fabIcon.innerHTML = PulsoAvatar({ state: newState, size: 74 });
  const headerIcon = document.getElementById('pulso-header-avatar');
  if (headerIcon) headerIcon.innerHTML = PulsoAvatar({ state: newState, size: 44 });

  document.querySelectorAll('.pulso-state-chip').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.state === newState);
  });
}

function togglePulsoPanel(forceOpen) {
  const next = typeof forceOpen === 'boolean' ? forceOpen : !_PulsoState.isOpen;
  _PulsoState.isOpen = next;
  const panel = document.getElementById('pulso-chat-panel');
  const fab = document.getElementById('pulso-fab-btn');
  const bubble = document.getElementById('pulso-greeting-bubble');

  if (panel) {
    panel.classList.toggle('open', next);
    panel.setAttribute('aria-hidden', next ? 'false' : 'true');
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

function _appendPulsoWelcomeMessage() {
  _PulsoState.messages.push({
    role: 'assistant',
    text: (
      'Hola, soy **Pulso**, tu asistente con **IA 100% local**.\n' +
      'Puedo generar el **resumen previo del paciente**, estructurar un **borrador SOAP** a partir de tu dictado (marcando `[PENDIENTE]` lo no dicho) o **buscar pacientes y citas** en lenguaje natural.\n\n' +
      '⚠️ *Revisar siempre las sugerencias por el médico.*'
    ),
  });
  _renderPulsoMessages();
}

function clearPulsoConversation() {
  _PulsoState.messages = [];
  _PulsoState.lastSoapStructured = null;
  _appendPulsoWelcomeMessage();
  setPulsoAvatarState('reposo');
  fetch(`${API}/api/pulso/audit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action: 'PULSO_BORRAR_CONVERSACION', engine: 'local_memory' }),
  }).catch(() => {});
  if (typeof showToast === 'function') {
    showToast('🧹 Conversación de Pulso borrada de la memoria local', 'info');
  }
}

async function checkPulsoLocalAiStatus() {
  const dot = document.getElementById('pulso-conn-dot');
  const lbl = document.getElementById('pulso-conn-label');
  const cfgBadge = document.getElementById('cfg-pulso-status-badge');

  // 1. Intentar conexión directa al servidor local Ollama (http://localhost:11434/api/tags)
  let directOllamaOk = false;
  let directModels = [];
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 1400);
    const r = await fetch(`${_PulsoState.ollamaUrl.replace(/\/$/, '')}/api/tags`, { signal: ctrl.signal });
    clearTimeout(timer);
    if (r.ok) {
      const d = await r.json();
      directOllamaOk = true;
      directModels = (d.models || []).map(m => m.name).filter(Boolean);
    }
  } catch (_) {}

  // 2. Consultar también al backend local (/api/pulso/status)
  try {
    const res = await fetch(`${API}/api/pulso/status?ollama_url=${encodeURIComponent(_PulsoState.ollamaUrl)}`);
    if (res.ok) {
      const data = await res.json();
      _PulsoState.ollamaConnected = directOllamaOk || !!data.ollama_connected;
      _PulsoState.availableModels = directModels.length ? directModels : (data.available_models || []);
      _PulsoState.statusLabel = _PulsoState.ollamaConnected
        ? `IA local conectada (Ollama · ${_PulsoState.model})`
        : 'Ollama desconectado · IA Clínica Local integrada activa';
    }
  } catch (_) {
    _PulsoState.ollamaConnected = directOllamaOk;
    _PulsoState.statusLabel = directOllamaOk
      ? `IA local conectada (Ollama · ${_PulsoState.model})`
      : 'IA local desconectada';
  }

  if (dot) {
    dot.className = `pulso-status-dot ${_PulsoState.ollamaConnected ? 'online' : 'fallback'}`;
  }
  if (lbl) {
    lbl.textContent = _PulsoState.statusLabel;
  }
  if (cfgBadge) {
    cfgBadge.textContent = _PulsoState.ollamaConnected
      ? `🟢 IA local conectada (${_PulsoState.model})`
      : '🟡 Ollama desconectado (Motor Local Integrado Activo)';
  }
}

async function saveAndTestPulsoConfig() {
  const urlInp = document.getElementById('cfg-pulso-url');
  const modInp = document.getElementById('cfg-pulso-model');
  const outBox = document.getElementById('cfg-pulso-test-out');

  const url = (urlInp?.value || 'http://localhost:11434').trim().replace(/\/$/, '');
  const model = (modInp?.value || 'qwen2.5:7b-instruct').trim();

  _PulsoState.ollamaUrl = url;
  _PulsoState.model = model;
  try {
    localStorage.setItem('medicaition_pulso_ollama_url', url);
    localStorage.setItem('medicaition_pulso_model', model);
  } catch (_) {}

  if (outBox) {
    outBox.style.display = 'block';
    outBox.textContent = `Probando conexión con ${url} y modelo ${model}...`;
  }

  try {
    const res = await fetch(`${API}/api/pulso/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ollama_url: url, model }),
    });
    const data = await res.json();
    await checkPulsoLocalAiStatus();
    const conn = data.connection || {};
    if (outBox) {
      outBox.innerHTML = conn.ollama_connected
        ? `✅ <strong>IA local conectada:</strong> Ollama activo en <code>${_pulsoEsc(url)}</code>. Modelos detectados: ${_pulsoEsc((conn.available_models || []).join(', ') || model)}.`
        : `ℹ️ <strong>Ollama no detectado en <code>${_pulsoEsc(url)}</code>:</strong> Pulso funciona automáticamente con el <strong>Motor Clínico Local Integrado</strong> (ChromaDB CIE-10 + Extractor SOAP Offline). Para activar un LLM pesado en Ollama ejecuta: <code>ollama run ${_pulsoEsc(model)}</code>.`;
    }
    if (typeof showToast === 'function') {
      showToast('Configuración de Pulso IA Local guardada', 'success');
    }
  } catch (err) {
    if (outBox) outBox.textContent = 'Error verificando IA local: ' + err.message;
  }
}

function _formatPulsoMarkdown(md) {
  let safe = _pulsoEsc(md || '');
  safe = safe.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  safe = safe.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  safe = safe.replace(/`([^`]+)`/g, '<code>$1</code>');
  safe = safe.replace(/\[PENDIENTE([^\]]*)\]/g, '<span class="pulso-pending-tag">[PENDIENTE$1]</span>');
  safe = safe.replace(/^### (.+)$/gm, '<div class="pulso-msg-h3">$1</div>');
  safe = safe.replace(/\n/g, '<br/>');
  return safe;
}

function _renderPulsoMessages() {
  const container = document.getElementById('pulso-chat-messages');
  if (!container) return;

  container.innerHTML = _PulsoState.messages.map((m, idx) => {
    const isUser = m.role === 'user';
    const hasSoap = !isUser && m.soapStructured && idx === _PulsoState.messages.length - 1;
    return `
      <div class="pulso-msg ${isUser ? 'pulso-msg-user' : 'pulso-msg-bot'}">
        <div class="pulso-msg-body">${isUser ? _pulsoEsc(m.text) : _formatPulsoMarkdown(m.text)}</div>
        ${hasSoap ? `
          <button type="button" class="pulso-apply-soap-btn" onclick="applyPulsoSoapToExpediente()">
            📋 Pasar borrador SOAP al Expediente Activo
          </button>
        ` : ''}
      </div>
    `;
  }).join('');

  container.scrollTop = container.scrollHeight;
}

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
  if (_PulsoState.isStreaming) return;
  const input = document.getElementById('pulso-chat-input');
  const prompt = (presetText != null ? presetText : (input?.value || '')).trim();
  if (!prompt) return;

  if (presetText == null && input) input.value = '';

  _PulsoState.messages.push({ role: 'user', text: prompt });
  _PulsoState.messages.push({ role: 'assistant', text: '' });
  const botIdx = _PulsoState.messages.length - 1;
  _PulsoState.isStreaming = true;
  setPulsoAvatarState('pensando');
  _renderPulsoMessages();

  const activeCurp = (typeof _ExpCareState !== 'undefined' && _ExpCareState.curp)
    || (window.AppState && window.AppState.selectedPatientCurp)
    || document.getElementById('curp-input')?.value?.trim()
    || '';

  try {
    const res = await fetch(`${API}/api/pulso/chat-stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        prompt,
        curp: activeCurp,
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
            if (evt.soap_structured) {
              _PulsoState.lastSoapStructured = evt.soap_structured;
              _PulsoState.messages[botIdx].soapStructured = evt.soap_structured;
            }
          } else if (evt.type === 'token' && evt.content) {
            _PulsoState.messages[botIdx].text += evt.content;
            _renderPulsoMessages();
          }
        } catch (_) {}
      }
    }

    setPulsoAvatarState(finalState);
  } catch (err) {
    _PulsoState.messages[botIdx].text =
      `⚠️ Error comunicando con el motor local: ${err.message}. Verifica que el servidor local esté activo.`;
    setPulsoAvatarState('alerta');
    _renderPulsoMessages();
  } finally {
    _PulsoState.isStreaming = false;
    _renderPulsoMessages();
  }
}

function runPulsoQuickAction(kind) {
  if (kind === 'summary') {
    sendPulsoPrompt('Dame el resumen previo del paciente actual con sus alergias, signos vitales y últimas consultas.');
  } else if (kind === 'soap') {
    const input = document.getElementById('pulso-chat-input');
    const typed = input?.value?.trim();
    if (typed) {
      input.value = '';
      sendPulsoPrompt(`Genera borrador de nota SOAP para: ${typed}`);
    } else {
      sendPulsoPrompt('Genera un borrador de nota SOAP para paciente con dolor abdominal de 2 días en epigastrio, fiebre 37.8 C, FC 82, TA 128/82.');
    }
  } else if (kind === 'search') {
    sendPulsoPrompt('Busca los pacientes registrados y las citas programadas en la agenda.');
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

// ---------------------------------------------------------------------------
// Movimiento Libre por Toda la Pantalla (Drag & Drop) + "Volver a la esquina"
// ---------------------------------------------------------------------------

function resetPulsoToCorner() {
  const root = document.getElementById('pulso-floating-root');
  if (!root) return;
  root.style.left = 'auto';
  root.style.top = 'auto';
  root.style.right = '24px';
  root.style.bottom = '24px';
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
  const root = document.getElementById('pulso-floating-root');
  if (!fab || !root) return;

  fab.addEventListener('pointerdown', (e) => {
    if (e.button !== undefined && e.button !== 0) return;
    const rect = root.getBoundingClientRect();
    _PulsoState.drag.active = true;
    _PulsoState.drag.moved = false;
    _PulsoState.drag.startX = e.clientX;
    _PulsoState.drag.startY = e.clientY;
    _PulsoState.drag.origLeft = rect.left;
    _PulsoState.drag.origTop = rect.top;
    fab.setPointerCapture?.(e.pointerId);
  });

  fab.addEventListener('pointermove', (e) => {
    if (!_PulsoState.drag.active) return;
    const dx = e.clientX - _PulsoState.drag.startX;
    const dy = e.clientY - _PulsoState.drag.startY;
    if (Math.hypot(dx, dy) > 6) {
      _PulsoState.drag.moved = true;
    }
    if (!_PulsoState.drag.moved) return;

    const maxLeft = Math.max(16, window.innerWidth - 96);
    const maxTop = Math.max(16, window.innerHeight - 104);
    const newLeft = Math.min(maxLeft, Math.max(16, _PulsoState.drag.origLeft + dx));
    const newTop = Math.min(maxTop, Math.max(16, _PulsoState.drag.origTop + dy));

    root.style.right = 'auto';
    root.style.bottom = 'auto';
    root.style.left = `${newLeft}px`;
    root.style.top = `${newTop}px`;
    root.classList.toggle('pulso-left-side', newLeft < 400);
  });

  const endDrag = (e) => {
    if (!_PulsoState.drag.active) return;
    const wasMoved = _PulsoState.drag.moved;
    _PulsoState.drag.active = false;
    fab.releasePointerCapture?.(e.pointerId);
    if (!wasMoved) {
      togglePulsoPanel();
    }
  };

  fab.addEventListener('pointerup', endDrag);
  fab.addEventListener('pointercancel', endDrag);

  // Soporte de teclado accesible (Enter / Space) en el botón flotante
  fab.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      togglePulsoPanel();
    }
  });
}

function initPulsoAssistant() {
  const fabAvatar = document.getElementById('pulso-fab-avatar');
  if (fabAvatar) fabAvatar.innerHTML = PulsoAvatar({ state: 'reposo', size: 74 });
  const headerAvatar = document.getElementById('pulso-header-avatar');
  if (headerAvatar) headerAvatar.innerHTML = PulsoAvatar({ state: 'reposo', size: 44 });

  const urlInp = document.getElementById('cfg-pulso-url');
  if (urlInp) urlInp.value = _PulsoState.ollamaUrl;
  const modInp = document.getElementById('cfg-pulso-model');
  if (modInp) modInp.value = _PulsoState.model;

  _initPulsoDraggable();
  checkPulsoLocalAiStatus();

  // Atajo global Ctrl+J / Cmd+J
  window.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'j') {
      e.preventDefault();
      togglePulsoPanel();
    } else if (e.key === 'Escape' && _PulsoState.isOpen) {
      togglePulsoPanel(false);
    }
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initPulsoAssistant);
} else {
  initPulsoAssistant();
}
