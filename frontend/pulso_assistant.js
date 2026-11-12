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
 * Renderiza el SVG inline del componente <PulsoAvatar /> con estética CYBER-MED:
 * - Corona triple de cristales de hielo/cuarzo luminosos arriba del casco.
 * - Casco monitor clínico azul acero (#1E40AF / #3B82F6, contorno #0F172A)
 *   con pantalla oscura (#08142C), emblema Caduceo médico brillante, texto "CYBER-MED",
 *   doble trazo ECG animado, matraz químico, cruz médica y termómetro digital inferior.
 * - Cuerpo robótico con pantalla de pulso en el pecho, vestido con bata médica blanca,
 *   emblema de engranaje en el hombro, bolsillo con instrumental clínico, brazo mecánico
 *   auxiliar dorsal y jeringa luminosa en la mano derecha.
 * - Piernas y botas robóticas articuladas con animación continua de caminata (walk cycle),
 *   flotación, saludo y salto elástico al darle clic.
 */
let _pulsoSvgSeq = 0;

function PulsoAvatar({ state = 'reposo', size = 104 } = {}) {
  const st = ['reposo', 'escuchando', 'pensando', 'alerta', 'contento'].includes(state)
    ? state
    : 'reposo';
  const uid = `pm${++_pulsoSvgSeq}`;

  const isAlert = st === 'alerta';
  const isThinking = st === 'pensando';
  const isListening = st === 'escuchando';
  const isHappy = st === 'contento';

  const hudPrimary = isAlert ? '#F59E0B' : (isHappy ? '#34D399' : '#5EEAD3');
  const hudSecondary = isAlert ? '#EF4444' : '#38BDF8';
  const crystalMid = isAlert ? '#FBBF24' : '#67E8F9';

  let visorOverlay = '';
  if (isThinking) {
    visorOverlay = `
      <g class="pulso-thinking-dots" fill="${hudPrimary}">
        <rect x="44" y="55" width="7" height="7" rx="1.5" class="pulso-dot d1" />
        <rect x="57" y="55" width="7" height="7" rx="1.5" class="pulso-dot d2" />
        <rect x="70" y="55" width="7" height="7" rx="1.5" class="pulso-dot d3" />
      </g>
    `;
  } else {
    visorOverlay = `
      <!-- Doble línea de ECG en vivo dentro del monitor CYBER-MED -->
      <g class="pulso-eyes ${st === 'reposo' || st === 'contento' ? 'can-blink' : ''}">
        <!-- Trazo ECG 1 -->
        <polyline class="pulso-ecg-line" points="40,51 47,51 49,45 51.5,56 54,49 56,51 62,51 64,44 66.5,56 69,51 74,51"
          fill="none" stroke="${hudPrimary}" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round" />
        <!-- Trazo ECG 2 -->
        <polyline class="pulso-ecg-line" points="40,61 46,61 48.5,56 51,65 53.5,59 56,61 61,61 63.5,55 66,65 68.5,61 74,61"
          fill="none" stroke="${hudPrimary}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" opacity="0.9" />
      </g>
    `;
  }

  const soundWaves = isListening ? `
    <g class="pulso-sound-waves" fill="none" stroke="#22D3EE" stroke-width="2.6" stroke-linecap="round">
      <path class="wave w1" d="M 118 42 Q 126 52 118 62" />
      <path class="wave w2" d="M 124 35 Q 135 52 124 69" />
      <path class="wave w1" d="M 22 42 Q 14 52 22 62" />
      <path class="wave w2" d="M 16 35 Q 5 52 16 69" />
    </g>
  ` : '';

  return `
    <div class="pulso-3d-stage" style="width:${size}px; height:${size}px;">
    <svg class="pulso-avatar-svg cyber-med-avatar state-${st}" width="${size}" height="${size}" viewBox="0 0 140 156" role="img" aria-label="Modelo 3D Cyber-Med en estado ${st}">
      <defs>
        <linearGradient id="${uid}_crystal" x1="35" y1="2" x2="100" y2="40" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#FFFFFF" />
          <stop offset="30%" stop-color="#A5F3FC" />
          <stop offset="65%" stop-color="${crystalMid}" />
          <stop offset="100%" stop-color="#0369A1" />
        </linearGradient>
        <radialGradient id="${uid}_armor3d" cx="35%" cy="22%" r="78%">
          <stop offset="0%" stop-color="#93C5FD" />
          <stop offset="32%" stop-color="#3B82F6" />
          <stop offset="72%" stop-color="#1D4ED8" />
          <stop offset="100%" stop-color="#0F172A" />
        </radialGradient>
        <linearGradient id="${uid}_armorSide" x1="20" y1="25" x2="120" y2="90" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#1E3A8A" />
          <stop offset="50%" stop-color="#172554" />
          <stop offset="100%" stop-color="#090D16" />
        </linearGradient>
        <radialGradient id="${uid}_screen" cx="50%" cy="40%" r="70%">
          <stop offset="0%" stop-color="#0F2942" />
          <stop offset="65%" stop-color="#09152B" />
          <stop offset="100%" stop-color="#020617" />
        </radialGradient>
        <linearGradient id="${uid}_coat" x1="35" y1="84" x2="108" y2="136" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#FFFFFF" />
          <stop offset="52%" stop-color="#F8FAFC" />
          <stop offset="82%" stop-color="#CBD5E1" />
          <stop offset="100%" stop-color="#64748B" />
        </linearGradient>
        <radialGradient id="${uid}_joint" cx="32%" cy="30%" r="70%">
          <stop offset="0%" stop-color="#BAE6FD" />
          <stop offset="45%" stop-color="#2563EB" />
          <stop offset="100%" stop-color="#0F172A" />
        </radialGradient>
      </defs>

      <!-- Sombra 3D proyectada en el piso con profundidad -->
      <ellipse class="pulso-floor-shadow" cx="70" cy="149" rx="38" ry="6.5" fill="#020617" opacity="0.38" />
      <ellipse class="pulso-floor-shadow" cx="70" cy="149" rx="22" ry="3.5" fill="#0F172A" opacity="0.55" />

      <!-- RIG 3D PRINCIPAL DEL PERSONAJE CYBER-MED -->
      <g class="pulso-character-rig">

        <!-- 1. BRAZO MECÁNICO QUIRÚRGICO DORSAL 3D -->
        <g class="pulso-mech-servo pulso-3d-layer-back">
          <line x1="46" y1="98" x2="31" y2="85" stroke="#0F172A" stroke-width="5" stroke-linecap="round" />
          <line x1="46" y1="98" x2="31" y2="85" stroke="#60A5FA" stroke-width="2.4" stroke-linecap="round" />
          <line x1="37" y1="91" x2="26" y2="98" stroke="#1E293B" stroke-width="3" stroke-linecap="round" />
          <path d="M 26 98 L 20 95 M 26 98 L 22 102" stroke="#E2E8F0" stroke-width="2.2" stroke-linecap="round" />
          <line x1="21" y1="99" x2="34" y2="106" stroke="#EF4444" stroke-width="1.6" stroke-dasharray="2 1" />
          <circle cx="29" cy="83" r="4.8" fill="url(#${uid}_joint)" stroke="#0F172A" stroke-width="2" />
          <circle cx="29" cy="83" r="1.8" fill="#EF4444" />
          <path d="M 29 78 L 27 71 M 25 80 L 18 75 M 24 84 L 17 85 M 32 79 L 37 73" stroke="#E2E8F0" stroke-width="2.2" stroke-linecap="round" />
        </g>

        <!-- 2. PIERNAS ROBÓTICAS CILÍNDRICAS 3D CON CICLO DE CAMINATA -->
        <g class="pulso-foot-left pulso-leg-left">
          <rect x="49" y="124" width="15" height="17" rx="5" fill="url(#${uid}_armor3d)" stroke="#0F172A" stroke-width="2.4" />
          <ellipse cx="56.5" cy="132" rx="6" ry="2.2" fill="#93C5FD" opacity="0.7" />
          <path d="M 45 139 Q 57 134 66 139 L 67 146 L 44 146 Z" fill="url(#${uid}_armor3d)" stroke="#0F172A" stroke-width="2.5" stroke-linejoin="round" />
          <path d="M 48 141 Q 56 138 63 141" fill="none" stroke="#BAE6FD" stroke-width="1.6" stroke-linecap="round" />
        </g>
        <g class="pulso-foot-right pulso-leg-right">
          <rect x="76" y="124" width="15" height="17" rx="5" fill="url(#${uid}_armor3d)" stroke="#0F172A" stroke-width="2.4" />
          <ellipse cx="83.5" cy="132" rx="6" ry="2.2" fill="#93C5FD" opacity="0.7" />
          <path d="M 74 139 Q 83 134 95 139 L 96 146 L 73 146 Z" fill="url(#${uid}_armor3d)" stroke="#0F172A" stroke-width="2.5" stroke-linejoin="round" />
          <path d="M 77 141 Q 85 138 92 141" fill="none" stroke="#BAE6FD" stroke-width="1.6" stroke-linecap="round" />
        </g>

        <!-- 3. TORSO ROBÓTICO 3D Y BATA MÉDICA ESCULPIDA CON VOLUMEN -->
        <g class="pulso-torso-rig pulso-3d-layer-mid">
          <!-- Sombra lateral 3D de extrusión del torso -->
          <rect x="52" y="84" width="36" height="45" rx="7" fill="url(#${uid}_armorSide)" stroke="#0F172A" stroke-width="2.4" />
          <!-- Monitor ECG de pecho con cristal curvo -->
          <rect x="57" y="88" width="26" height="16" rx="4" fill="url(#${uid}_screen)" stroke="#38BDF8" stroke-width="1.8" />
          <polyline class="pulso-ecg-line" points="59,96 64,96 66.5,91 69,101 71.5,94 74,96 81,96" fill="none" stroke="${hudPrimary}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          <!-- Cinturón pélvico 3D con bisel iluminado -->
          <rect x="55" y="113" width="30" height="13" rx="4" fill="url(#${uid}_armor3d)" stroke="#0F172A" stroke-width="2.2" />
          <path d="M 70 116.5 V 122.5 M 67 119.5 H 73" stroke="#EF4444" stroke-width="2.8" stroke-linecap="round" />

          <!-- Lado izquierdo de la bata blanca con pliegue 3D -->
          <path d="M 43 84 L 60 84 L 60 133 L 40 133 Z" fill="url(#${uid}_coat)" stroke="#0F172A" stroke-width="2.5" stroke-linejoin="round" />
          <path d="M 45 87 L 43 130" stroke="#FFFFFF" stroke-width="2.2" stroke-linecap="round" opacity="0.9" />
          <polygon points="51,84 60,84 60,105 50,96" fill="#E2E8F0" stroke="#0F172A" stroke-width="2" stroke-linejoin="round" />

          <!-- Lado derecho de la bata blanca con pliegue 3D -->
          <path d="M 80 84 L 97 84 L 100 133 L 80 133 Z" fill="url(#${uid}_coat)" stroke="#0F172A" stroke-width="2.5" stroke-linejoin="round" />
          <path d="M 94 87 L 96 130" stroke="#94A3B8" stroke-width="2" stroke-linecap="round" opacity="0.6" />
          <polygon points="89,84 80,84 80,105 90,96" fill="#E2E8F0" stroke="#0F172A" stroke-width="2" stroke-linejoin="round" />

          <!-- Bolsillo 3D izquierdo con otoscopio volumétrico -->
          <rect x="45" y="108" width="12" height="9" rx="2" fill="#94A3B8" stroke="#0F172A" stroke-width="1.8" />
          <circle cx="54" cy="108" r="2" fill="#EF4444" />
          <rect x="45" y="113" width="14" height="14" rx="3.5" fill="#334155" stroke="#0F172A" stroke-width="2.2" />
          <path d="M 47 115 H 57" stroke="#64748B" stroke-width="1.5" stroke-linecap="round" />

          <!-- Bolsillo 3D derecho con pluma clínica -->
          <rect x="83" y="113" width="12" height="14" rx="2.5" fill="#E2E8F0" stroke="#334155" stroke-width="1.8" />
          <rect x="85" y="106" width="4" height="9" rx="2" fill="url(#${uid}_joint)" stroke="#0F172A" stroke-width="1.5" />
        </g>

        <!-- 4. BRAZO IZQUIERDO ESFÉRICO 3D -->
        <g class="pulso-arm-left pulso-3d-layer-front">
          <path d="M 45 85 L 33 108 L 44 113 L 50 94 Z" fill="url(#${uid}_coat)" stroke="#0F172A" stroke-width="2.4" stroke-linejoin="round" />
          <circle cx="43" cy="96" r="4.2" fill="#DBEAFE" stroke="#1E40AF" stroke-width="1.6" stroke-dasharray="2 1" />
          <circle cx="43" cy="96" r="1.6" fill="#EF4444" />
          <circle cx="37.5" cy="114.5" r="6.8" fill="url(#${uid}_joint)" stroke="#0F172A" stroke-width="2.4" />
        </g>

        <!-- 5. BRAZO DERECHO ESFÉRICO 3D CON JERINGA DE CRISTAL LUMINOSA -->
        <g class="pulso-arm-right pulso-3d-layer-front">
          <path d="M 95 85 L 107 108 L 96 113 L 90 94 Z" fill="url(#${uid}_coat)" stroke="#0F172A" stroke-width="2.4" stroke-linejoin="round" />
          <circle cx="102.5" cy="114.5" r="6.8" fill="url(#${uid}_joint)" stroke="#0F172A" stroke-width="2.4" />
          <g transform="rotate(-38 103 104)">
            <rect x="98.5" y="91" width="8" height="16" rx="2.5" fill="#34D399" stroke="#0F172A" stroke-width="2" />
            <rect x="100" y="92.5" width="2.2" height="13" rx="1" fill="#A7F3D0" opacity="0.85" />
            <line x1="100" y1="96" x2="105" y2="96" stroke="#064E3B" stroke-width="1.4" />
            <line x1="100" y1="100" x2="105" y2="100" stroke="#064E3B" stroke-width="1.4" />
            <line x1="102.5" y1="85" x2="102.5" y2="91" stroke="#CBD5E1" stroke-width="2.4" />
            <line x1="99" y1="85" x2="106" y2="85" stroke="#0F172A" stroke-width="2.4" stroke-linecap="round" />
            <line x1="102.5" y1="107" x2="102.5" y2="115" stroke="#7DD3FC" stroke-width="2" stroke-linecap="round" />
          </g>
        </g>

        <!-- 6. CABEZA MONITOR 3D VOLUMÉTRICA + CORONA DE CRISTALES FACETADOS -->
        <g class="pulso-head-rig pulso-3d-layer-head">
          <!-- CORONA DE 3 CRISTALES 3D CON CARAS DE LUZ Y SOMBRA -->
          <g class="pulso-antenna-rig">
            <!-- Cristal izquierdo 3D -->
            <polygon points="30,34 39,13 53,23 47,34" fill="url(#${uid}_crystal)" stroke="#0F172A" stroke-width="2.5" stroke-linejoin="round" />
            <polygon points="39,13 44,34 30,34" fill="#FFFFFF" opacity="0.42" />
            <!-- Cristal derecho 3D -->
            <polygon points="87,23 101,14 110,34 93,34" fill="url(#${uid}_crystal)" stroke="#0F172A" stroke-width="2.5" stroke-linejoin="round" />
            <polygon points="101,14 96,34 87,23" fill="#FFFFFF" opacity="0.42" />
            <!-- Gran cristal central 3D -->
            <polygon class="pulso-antenna-tip" points="50,26 70,2 90,26 84,33 56,33" fill="url(#${uid}_crystal)" stroke="#0F172A" stroke-width="2.8" stroke-linejoin="round" />
            <polygon points="70,2 70,32 52,26" fill="#FFFFFF" opacity="0.5" />
            <polygon points="70,2 88,26 70,32" fill="#0284C7" opacity="0.32" />
            <line x1="70" y1="3" x2="70" y2="31" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" />
          </g>

          <!-- Extrusión trasera 3D del casco (da grosor real de bloque 3D) -->
          <rect x="24" y="27" width="92" height="61" rx="17" fill="url(#${uid}_armorSide)" stroke="#0F172A" stroke-width="2.8" />

          <!-- Módulos auriculares 3D esféricos laterales -->
          <rect x="18" y="41" width="10" height="29" rx="5" fill="url(#${uid}_joint)" stroke="#0F172A" stroke-width="2.5" />
          <ellipse cx="22.5" cy="54" rx="2.4" ry="8" fill="#BAE6FD" opacity="0.85" />
          <rect x="112" y="41" width="10" height="29" rx="5" fill="url(#${uid}_joint)" stroke="#0F172A" stroke-width="2.5" />
          <ellipse cx="116.5" cy="54" rx="2.4" ry="8" fill="#BAE6FD" opacity="0.85" />

          <!-- Carcasa frontal 3D del casco monitor -->
          <rect x="27" y="24" width="86" height="60" rx="16" fill="url(#${uid}_armor3d)" stroke="#0F172A" stroke-width="2.8" />
          <!-- Brillo especular 3D superior e izquierdo -->
          <path d="M 38 28.5 H 102" stroke="#E0F2FE" stroke-width="3" stroke-linecap="round" opacity="0.9" />
          <path d="M 31 36 V 72" stroke="#93C5FD" stroke-width="2.2" stroke-linecap="round" opacity="0.65" />

          <!-- Bisel interior hundido 3D de la pantalla -->
          <rect x="33" y="30" width="74" height="49" rx="11" fill="#020617" stroke="#1E3A8A" stroke-width="2.2" />
          <rect x="35" y="32" width="70" height="45" rx="9.5" fill="url(#${uid}_screen)" />

          <!-- CADUCEO MÉDICO HOLOGRÁFICO 3D -->
          <g class="pulso-caduceus" stroke="${hudPrimary}" fill="none" stroke-linecap="round">
            <path d="M 70 38 C 63 33, 56 35, 53 39 C 58 40, 64 40, 70 39 Z" fill="${hudPrimary}" opacity="0.92" />
            <path d="M 70 38 C 77 33, 84 35, 87 39 C 82 40, 76 40, 70 39 Z" fill="${hudPrimary}" opacity="0.92" />
            <line x1="70" y1="34" x2="70" y2="49" stroke-width="1.9" />
            <circle cx="70" cy="33.5" r="1.8" fill="#FFFFFF" />
            <path d="M 66 39 Q 74 42 66 45 Q 74 48 70 49" stroke-width="1.4" />
            <path d="M 74 39 Q 66 42 74 45 Q 66 48 70 49" stroke-width="1.4" />
          </g>

          <!-- Etiqueta holográfica "CYBER-MED" -->
          <text x="39" y="44" fill="${hudPrimary}" font-family="monospace, sans-serif" font-size="6.2" font-weight="800" letter-spacing="0.4">CYBER-MED</text>

          <!-- Panel derecho del HUD: Matraz químico + barras + Cruz Médica -->
          <rect x="78" y="40" width="22" height="16" rx="2.5" fill="#0F2942" stroke="${hudSecondary}" stroke-width="1.2" />
          <path d="M 87 43 H 91 M 88 43 V 46 L 85 52 H 93 L 90 46 V 43" fill="none" stroke="${hudPrimary}" stroke-width="1.4" stroke-linejoin="round" />
          <line x1="86" y1="50" x2="92" y2="50" stroke="${hudPrimary}" stroke-width="1.6" />

          <line x1="79" y1="59" x2="92" y2="59" stroke="${hudPrimary}" stroke-width="2" />
          <line x1="79" y1="62.5" x2="87" y2="62.5" stroke="#93C5FD" stroke-width="2" />

          <!-- Recuadro de Cruz Médica inferior derecha -->
          <rect x="79" y="65" width="21" height="11" rx="2.2" fill="#0F2942" stroke="${hudPrimary}" stroke-width="1.4" />
          <path d="M 89.5 67.5 V 73.5 M 86.5 70.5 H 92.5" stroke="${hudPrimary}" stroke-width="2.3" stroke-linecap="round" />

          <!-- Trazos ECG o puntos de pensamiento a la izquierda -->
          ${visorOverlay}

          <!-- Barras de progreso inferiores izquierdas -->
          <rect x="40" y="66" width="33" height="2.8" rx="1" fill="#1E293B" />
          <rect x="40" y="66" width="23" height="2.8" rx="1" fill="#E0F2FE" />
          <rect x="40" y="70.5" width="33" height="2.8" rx="1" fill="#1E293B" />
          <rect x="40" y="70.5" width="19" height="2.8" rx="1" fill="${hudPrimary}" />

          <!-- Termómetro digital 3D blanco en la base del visor -->
          <rect x="59" y="74" width="23" height="4.5" rx="2.2" fill="#F8FAFC" stroke="#0F172A" stroke-width="1.2" />
          <rect x="63" y="75.2" width="9" height="2.1" rx="0.6" fill="#0F172A" />
          <path d="M 82 75 L 87 76.2 L 82 77.5 Z" fill="#CBD5E1" />

          <!-- Reflejo diagonal de cristal curvo 3D sobre la pantalla -->
          <path d="M 38 35 L 56 35 L 43 62 L 36 62 Z" fill="#FFFFFF" opacity="0.07" pointer-events="none" />

          ${soundWaves}
        </g>
      </g>
    </svg>
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

function togglePulsoPanel(forceOpen) {
  const next = typeof forceOpen === 'boolean' ? forceOpen : !_PulsoState.isOpen;
  _PulsoState.isOpen = next;
  const panel = document.getElementById('pulso-chat-panel');
  const fab = document.getElementById('pulso-fab-btn');
  const bubble = document.getElementById('pulso-greeting-bubble');

  if (panel) {
    panel.classList.toggle('open', next);
    panel.classList.toggle('is-open', next);
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
    dot.className = `pulso-conn-dot ${_PulsoState.ollamaConnected ? 'is-online' : 'is-local-fallback'}`;
  }
  if (lbl) {
    lbl.textContent = _PulsoState.statusLabel;
  }
  if (cfgBadge) {
    cfgBadge.className = `pulso-cfg-badge ${_PulsoState.ollamaConnected ? 'is-online' : 'is-fallback'}`;
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
      <div class="pulso-msg ${isUser ? 'pulso-msg-user' : 'pulso-msg-assistant'}">
        <div class="pulso-msg-bubble">${isUser ? _pulsoEsc(m.text) : _formatPulsoMarkdown(m.text)}</div>
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
  const header = document.querySelector('.pulso-chat-header');
  const root = document.getElementById('pulso-floating-root');
  if (!fab || !root) return;

  let suppressNextClick = false;

  const startDrag = (e, isFab) => {
    if (e.button !== undefined && e.button !== 0) return;
    if (!isFab && e.target.closest('button')) return;
    const rect = root.getBoundingClientRect();
    _PulsoState.drag.active = true;
    _PulsoState.drag.moved = false;
    _PulsoState.drag.startX = e.clientX;
    _PulsoState.drag.startY = e.clientY;
    _PulsoState.drag.origLeft = rect.left;
    _PulsoState.drag.origTop = rect.top;
    try { e.currentTarget.setPointerCapture?.(e.pointerId); } catch (_) {}
  };

  const moveDrag = (e) => {
    if (!_PulsoState.drag.active) return;
    const dx = e.clientX - _PulsoState.drag.startX;
    const dy = e.clientY - _PulsoState.drag.startY;
    if (Math.hypot(dx, dy) > 6) {
      _PulsoState.drag.moved = true;
    }
    if (!_PulsoState.drag.moved) return;

    const maxLeft = Math.max(12, window.innerWidth - 96);
    const maxTop = Math.max(12, window.innerHeight - 104);
    const newLeft = Math.min(maxLeft, Math.max(12, _PulsoState.drag.origLeft + dx));
    const newTop = Math.min(maxTop, Math.max(12, _PulsoState.drag.origTop + dy));

    root.style.right = 'auto';
    root.style.bottom = 'auto';
    root.style.left = `${newLeft}px`;
    root.style.top = `${newTop}px`;
    root.classList.toggle('pulso-left-side', newLeft < 400);
  };

  const endDrag = (e, isFab) => {
    if (!_PulsoState.drag.active) return;
    const wasMoved = _PulsoState.drag.moved;
    _PulsoState.drag.active = false;
    try { e.currentTarget.releasePointerCapture?.(e.pointerId); } catch (_) {}
    if (isFab && wasMoved) {
      suppressNextClick = true;
      setTimeout(() => { suppressNextClick = false; }, 200);
    }
  };

  fab.addEventListener('pointerdown', (e) => startDrag(e, true));
  fab.addEventListener('pointermove', moveDrag);
  fab.addEventListener('pointerup', (e) => endDrag(e, true));
  fab.addEventListener('pointercancel', (e) => endDrag(e, true));

  // Inclinación 3D en tiempo real al pasar el cursor (rotateX + rotateY)
  fab.addEventListener('pointermove', (e) => {
    if (_PulsoState.drag.active) return;
    const stage = fab.querySelector('.pulso-3d-stage');
    if (!stage) return;
    const r = fab.getBoundingClientRect();
    const nx = ((e.clientX - (r.left + r.width / 2)) / (r.width / 2));
    const ny = ((e.clientY - (r.top + r.height / 2)) / (r.height / 2));
    const rotY = Math.max(-22, Math.min(22, nx * 20));
    const rotX = Math.max(-18, Math.min(18, -ny * 16));
    stage.style.transform = `rotateX(${rotX.toFixed(1)}deg) rotateY(${rotY.toFixed(1)}deg) translateZ(8px)`;
  });

  fab.addEventListener('pointerleave', () => {
    const stage = fab.querySelector('.pulso-3d-stage');
    if (stage) stage.style.transform = '';
  });

  fab.addEventListener('click', (e) => {
    e.preventDefault();
    if (suppressNextClick) {
      suppressNextClick = false;
      return;
    }
    triggerPulsoClickReaction();
    togglePulsoPanel();
  });

  if (header) {
    header.addEventListener('pointerdown', (e) => startDrag(e, false));
    header.addEventListener('pointermove', moveDrag);
    header.addEventListener('pointerup', (e) => endDrag(e, false));
    header.addEventListener('pointercancel', (e) => endDrag(e, false));
  }
}

function initPulsoAssistant() {
  const fabAvatar = document.getElementById('pulso-fab-avatar');
  if (fabAvatar) fabAvatar.innerHTML = PulsoAvatar({ state: 'reposo', size: 106 });
  const headerAvatar = document.getElementById('pulso-header-avatar');
  if (headerAvatar) headerAvatar.innerHTML = PulsoAvatar({ state: 'reposo', size: 48 });

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
