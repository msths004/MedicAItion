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
 * Renderiza el SVG inline del asistente <PulsoAvatar />: "Dr. Oso" (El Oso Kawaii Médico)
 * - Adorable osito doctor con pelaje crema dorado, orejitas redondas y mechón fluffy.
 * - Enormes ojos anime kawaii con destellos brillantes y parpadeo natural.
 * - Chapitas sonrosadas (blush), hocico tierno y sonrisa amigable con lengüita rosa.
 * - Traje quirúrgico celeste pastel (scrubs) y bata médica blanca con gafete "DR. OSO".
 * - Estetoscopio rosa con pieza pectoral en forma de corazón latiendo en el pecho.
 * - Patita derecha levantada saludando alegremente (con almohadilla/huellita rosa).
 * - Patita izquierda sosteniendo una tablilla médica con hoja clínica y corazoncito sonriente.
 * - Estados interactivos: "reposo" (saludo kawaii), "escuchando" (orejitas atentas con destellos),
 *   "pensando" (patita en la barbilla y bombilla/chispas), "alerta" (ojitos atentos clínicos),
 *   "contento" (ojitos felices ^_^ y saltito de alegría).
 */
/**
 * DR. OSO (El Oso Kawaii Médico) - Avatar con ilustraciones oficiales idénticas
 * Usa los assets extraídos fielmente de las ilustraciones provistas por el usuario:
 * - reposo: Dr. Oso cuerpo completo saludando con bata, scrubs, estetoscopio y maletín.
 * - escuchando: Dr. Oso auscultando con otoscopio y signo de pregunta.
 * - pensando: Dr. Oso analizando radiografía cardíaca con bombilla de ideas.
 * - alerta: Dr. Oso llamada de emergencia con radio.
 * - contento: Dr. Oso con checklist y palomita verde de confirmación.
 */
const DR_OSO_ASSETS = {
  reposo: 'assets/dr_oso/dr_oso_reposo.png',
  escuchando: 'assets/dr_oso/dr_oso_escuchando.png',
  pensando: 'assets/dr_oso/dr_oso_pensando.png',
  alerta: 'assets/dr_oso/dr_oso_emergency_call.png',
  contento: 'assets/dr_oso/dr_oso_confirmed.png',
};

// Precarga inmediata de assets en segundo plano para cero latencia
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

function triggerPulsoClickReaction() {
  const fab = document.getElementById('pulso-fab-btn');
  if (fab) {
    fab.classList.remove('pulso-clicked-boing');
    void fab.offsetWidth; // Force reflow to restart keyframe
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
  if (fabIcon) fabIcon.innerHTML = PulsoAvatar({ state: newState, size: 106 });
  const headerIcon = document.getElementById('pulso-header-avatar');
  if (headerIcon) headerIcon.innerHTML = PulsoAvatar({ state: newState, size: 48 });

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

  const panel = document.getElementById('pulso-chat-panel');

  const fab = document.getElementById('pulso-fab-btn');

  const bubble = document.getElementById('pulso-greeting-bubble');



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
    text: (
      'Hola, soy el **Dr. Oso** (Pulso), tu asistente médico con **IA 100% local** 🩺🐻.\n' +
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



  try {

    const apiBase = typeof API !== 'undefined' ? API : '';

    const res = await fetch(`${apiBase}/api/pulso/status?ollama_url=${encodeURIComponent(_PulsoState.ollamaUrl)}`);

    if (res.ok) {

      const data = await res.json();

      _PulsoState.ollamaConnected = directOllamaOk || !!data.ollama_connected;

      _PulsoState.availableModels = directModels.length ? directModels : (data.available_models || []);

      const activeEng = data.active_engine || (_PulsoState.ollamaConnected ? 'ollama_local' : 'embedded_clinical_local');

      if (activeEng === 'local_gguf_engine') {

        const mod = data.local_gguf?.model_name || 'OpenBioLLM-8B';

        _PulsoState.statusLabel = `🟢 IA Local Médica (GGUF: ${mod})`;

      } else if (activeEng === 'ollama_local' || _PulsoState.ollamaConnected) {

        _PulsoState.statusLabel = `🟢 IA Local Conectada (Ollama: ${_PulsoState.model})`;

      } else {

        _PulsoState.statusLabel = '🟢 Mini ChatGPT Clínico Local (IA Offline)';

      }

    }

  } catch (_) {

    _PulsoState.ollamaConnected = directOllamaOk;

    _PulsoState.statusLabel = directOllamaOk

      ? `🟢 IA Local Conectada (Ollama: ${_PulsoState.model})`

      : '🟢 Mini ChatGPT Clínico Local (IA Offline)';

  }



  if (dot) {

    dot.className = 'pulso-conn-dot is-online';

  }

  if (lbl) {

    lbl.textContent = _PulsoState.statusLabel;

  }

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
    let contentHtml = '';
    if (isUser) {
      contentHtml = _pulsoEsc(m.text);
    } else {
      if (!m.text && _PulsoState.isStreaming && idx === _PulsoState.messages.length - 1) {
        contentHtml = '<span class="pulso-typing-indicator"><span class="dot"></span><span class="dot"></span><span class="dot"></span> <em>Dr. Oso está procesando la consulta...</em></span>';
      } else {
        contentHtml = _formatPulsoMarkdown(m.text || '');
      }
    }
    return `
      <div class="pulso-msg ${isUser ? 'pulso-msg-user' : 'pulso-msg-assistant'}">
        <div class="pulso-msg-bubble">${contentHtml}</div>
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
  const input = document.getElementById('pulso-chat-input');
  const sendBtn = document.getElementById('pulso-send-btn');
  const prompt = (presetText != null ? presetText : (input?.value || '')).trim();

  console.log('[PulsoDebug] sendPulsoPrompt iniciado con:', prompt);

  if (_PulsoState.isStreaming) {
    console.warn('[PulsoDebug] Transmisión activa en curso, ignorando nuevo envío.');
    return;
  }
  if (!prompt) return;

  if (presetText == null && input) input.value = '';

  _PulsoState.messages.push({ role: 'user', text: prompt });
  _PulsoState.messages.push({ role: 'assistant', text: '' });
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
    console.log(`[PulsoDebug] Enviando POST a ${apiBase}/api/pulso/chat-stream para CURP: ${activeCurp}`);
    const res = await fetch(`${apiBase}/api/pulso/chat-stream`, {
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
    let tokensReceived = 0;

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
            tokensReceived++;
            _PulsoState.messages[botIdx].text += evt.content;
            _renderPulsoMessages();
          } else if (evt.type === 'done') {
            console.log('[PulsoDebug] Stream completado. Total tokens:', tokensReceived);
          }
        } catch (eJson) {
          console.warn('[PulsoDebug] NDJSON parse warning:', line, eJson);
        }
      }
    }

    setPulsoAvatarState(finalState);
  } catch (err) {
    console.error('[PulsoDebug] Error durante la consulta local:', err);
    _PulsoState.messages[botIdx].text =
      `⚠️ Error comunicando con el motor local: ${err.message}. Verifica que el backend esté activo en http://127.0.0.1:8000.`;
    setPulsoAvatarState('alerta');
    _renderPulsoMessages();
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



  const onPointerUp = (e) => {

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

  if (header) {

    header.onpointerdown = (e) => onPointerDown(e, false);

  }



  fab.onclick = (e) => {

    e.preventDefault();

    e.stopPropagation();

    if (justDragged || didMove) {

      return;

    }

    triggerPulsoClickReaction();

    togglePulsoPanel();

  };

}



function initPulsoAssistant() {

  const fabAvatar = document.getElementById('pulso-fab-avatar');

  if (fabAvatar) {

    fabAvatar.innerHTML = PulsoAvatar({ state: _PulsoState.avatarState || 'reposo', size: 106 });

  }

  const headerAvatar = document.getElementById('pulso-header-avatar');

  if (headerAvatar) {

    headerAvatar.innerHTML = PulsoAvatar({ state: _PulsoState.avatarState || 'reposo', size: 48 });

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

