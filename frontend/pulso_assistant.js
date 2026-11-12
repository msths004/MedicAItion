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
let _pulsoSvgSeq = 0;

function PulsoAvatar({ state = 'reposo', size = 110 } = {}) {
  const st = ['reposo', 'escuchando', 'pensando', 'alerta', 'contento'].includes(state)
    ? state
    : 'reposo';
  const uid = `oso${++_pulsoSvgSeq}`;

  const isAlert = st === 'alerta';
  const isThinking = st === 'pensando';
  const isListening = st === 'escuchando';
  const isHappy = st === 'contento';

  // Ojos según el estado
  let eyesContent = '';
  if (isHappy) {
    // Ojitos felices cerrados en arco ^_^
    eyesContent = `
      <path d="M 46 52 Q 53 45 60 52" fill="none" stroke="#3D2114" stroke-width="3.2" stroke-linecap="round" />
      <path d="M 80 52 Q 87 45 94 52" fill="none" stroke="#3D2114" stroke-width="3.2" stroke-linecap="round" />
      <circle cx="43" cy="48" r="1.5" fill="#FF859A" />
      <circle cx="97" cy="48" r="1.5" fill="#FF859A" />
    `;
  } else if (isThinking) {
    // Ojitos mirando hacia arriba con curiosidad
    eyesContent = `
      <g class="pulso-eyes can-blink">
        <!-- Ojo izquierdo -->
        <ellipse cx="53" cy="50" rx="8" ry="9.5" fill="url(#${uid}_eye)" stroke="#3D2114" stroke-width="1.6" />
        <ellipse cx="53" cy="54" rx="6" ry="4" fill="#D946EF" opacity="0.45" />
        <circle cx="52" cy="46" r="3.6" fill="#FFFFFF" />
        <circle cx="56.5" cy="50.5" r="1.8" fill="#FFFFFF" />
        <circle cx="50" cy="52" r="1" fill="#FFFFFF" />
        <!-- Ojo derecho -->
        <ellipse cx="87" cy="50" rx="8" ry="9.5" fill="url(#${uid}_eye)" stroke="#3D2114" stroke-width="1.6" />
        <ellipse cx="87" cy="54" rx="6" ry="4" fill="#D946EF" opacity="0.45" />
        <circle cx="86" cy="46" r="3.6" fill="#FFFFFF" />
        <circle cx="90.5" cy="50.5" r="1.8" fill="#FFFFFF" />
        <circle cx="84" cy="52" r="1" fill="#FFFFFF" />
      </g>
    `;
  } else {
    // Ojitos kawaii grandes y brillantes habituales
    eyesContent = `
      <g class="pulso-eyes ${st === 'reposo' ? 'can-blink' : ''}">
        <!-- Ojo izquierdo -->
        <ellipse cx="53" cy="51" rx="8.2" ry="9.8" fill="url(#${uid}_eye)" stroke="#3D2114" stroke-width="1.6" />
        <ellipse cx="53" cy="56" rx="6.2" ry="4" fill="#E879F9" opacity="0.5" />
        <circle cx="51" cy="47" r="3.8" fill="#FFFFFF" />
        <circle cx="56.5" cy="54" r="1.9" fill="#FFFFFF" />
        <circle cx="50" cy="53.5" r="1.1" fill="#FFFFFF" />
        <!-- Ojo derecho -->
        <ellipse cx="87" cy="51" rx="8.2" ry="9.8" fill="url(#${uid}_eye)" stroke="#3D2114" stroke-width="1.6" />
        <ellipse cx="87" cy="56" rx="6.2" ry="4" fill="#E879F9" opacity="0.5" />
        <circle cx="85" cy="47" r="3.8" fill="#FFFFFF" />
        <circle cx="90.5" cy="54" r="1.9" fill="#FFFFFF" />
        <circle cx="84" cy="53.5" r="1.1" fill="#FFFFFF" />
      </g>
    `;
  }

  // Cejitas tiernas
  const browsContent = isAlert
    ? `
      <path d="M 46 39 Q 52 36 58 40" fill="none" stroke="#5C3E29" stroke-width="2.2" stroke-linecap="round" />
      <path d="M 82 40 Q 88 36 94 39" fill="none" stroke="#5C3E29" stroke-width="2.2" stroke-linecap="round" />
    `
    : `
      <path d="M 47 41 Q 53 38 58 41" fill="none" stroke="#5C3E29" stroke-width="2" stroke-linecap="round" />
      <path d="M 82 41 Q 87 38 93 41" fill="none" stroke="#5C3E29" stroke-width="2" stroke-linecap="round" />
    `;

  // Boca adorable con lengüita
  let mouthContent = '';
  if (isThinking) {
    mouthContent = `
      <path d="M 68 64 Q 70 66 73 64" fill="none" stroke="#3D2114" stroke-width="2" stroke-linecap="round" />
    `;
  } else if (isAlert) {
    mouthContent = `
      <ellipse cx="70" cy="65" rx="2.8" ry="3.2" fill="#FF859A" stroke="#3D2114" stroke-width="1.6" />
    `;
  } else {
    mouthContent = `
      <path d="M 65 62 Q 70 65.5 70 62.5 Q 70 65.5 75 62" fill="none" stroke="#3D2114" stroke-width="2" stroke-linecap="round" />
      <path d="M 67.5 63 Q 70 68 72.5 63 Z" fill="#FF859A" />
    `;
  }

  // Burbuja de ideas o destellos
  let extraOverlay = '';
  if (isThinking) {
    extraOverlay = `
      <!-- Burbuja de idea con bombilla y corazoncito -->
      <g class="dr-oso-thought-bubble">
        <circle cx="108" cy="22" r="12" fill="#FFFFFF" stroke="#FBBF24" stroke-width="2" />
        <path d="M 104 20 C 104 16, 112 16, 112 20 C 112 23, 108 24, 108 26" fill="none" stroke="#F59E0B" stroke-width="2" stroke-linecap="round" />
        <circle cx="108" cy="29" r="1.2" fill="#F59E0B" />
        <!-- Rayos de luz -->
        <line x1="108" y1="6" x2="108" y2="3" stroke="#FBBF24" stroke-width="2" stroke-linecap="round" />
        <line x1="120" y1="12" x2="123" y2="10" stroke="#FBBF24" stroke-width="2" stroke-linecap="round" />
        <line x1="96" y1="12" x2="93" y2="10" stroke="#FBBF24" stroke-width="2" stroke-linecap="round" />
        <!-- Burbujitas conectadas -->
        <circle cx="98" cy="33" r="3.5" fill="#FFFFFF" stroke="#FBBF24" stroke-width="1.4" />
        <circle cx="93" cy="39" r="2" fill="#FFFFFF" stroke="#FBBF24" stroke-width="1.2" />
      </g>
    `;
  } else if (isListening) {
    extraOverlay = `
      <!-- Destellos de atención y ondas amigables -->
      <g class="dr-oso-listen-sparkles">
        <path d="M 20 30 Q 23 23 30 20 Q 23 17 20 10 Q 17 17 10 20 Q 17 23 20 30 Z" fill="#FDE047" opacity="0.9" transform="scale(0.6) translate(14, 12)" />
        <path d="M 120 30 Q 123 23 130 20 Q 123 17 120 10 Q 117 17 110 20 Q 117 23 120 30 Z" fill="#FDE047" opacity="0.9" transform="scale(0.6) translate(80, 12)" />
        <path d="M 18 48 Q 12 55 18 62" fill="none" stroke="#38BDF8" stroke-width="2.4" stroke-linecap="round" />
        <path d="M 122 48 Q 128 55 122 62" fill="none" stroke="#38BDF8" stroke-width="2.4" stroke-linecap="round" />
      </g>
    `;
  } else if (isAlert) {
    extraOverlay = `
      <!-- Signo de atención médica amigable -->
      <g class="dr-oso-alert-badge">
        <circle cx="106" cy="20" r="9" fill="#FEF3C7" stroke="#F59E0B" stroke-width="2" />
        <text x="106" y="24" text-anchor="middle" font-size="12" font-weight="900" fill="#D97706">!</text>
      </g>
    `;
  } else if (isHappy) {
    extraOverlay = `
      <!-- Corazoncitos flotantes de felicidad -->
      <g class="dr-oso-happy-hearts">
        <path d="M 22 28 C 22 22, 28 22, 30 25 C 32 22, 38 22, 38 28 C 38 34, 30 38, 30 38 C 30 38, 22 34, 22 28 Z" fill="#F472B6" transform="scale(0.5) translate(12, 10)" />
        <path d="M 22 28 C 22 22, 28 22, 30 25 C 32 22, 38 22, 38 28 C 38 34, 30 38, 30 38 C 30 38, 22 34, 22 28 Z" fill="#FB7185" transform="scale(0.6) translate(150, 8)" />
      </g>
    `;
  }

  return `
    <div class="pulso-3d-stage dr-oso-stage" style="width:${size}px; height:${size}px;">
    <svg class="pulso-avatar-svg dr-oso-avatar state-${st}" width="${size}" height="${size}" viewBox="0 0 140 156" role="img" aria-label="Dr. Oso Kawaii en estado ${st}">
      <defs>
        <!-- Pelaje suave crema dorado del Dr. Oso -->
        <linearGradient id="${uid}_fur" x1="40" y1="18" x2="100" y2="135" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#FFF8F0" />
          <stop offset="30%" stop-color="#FCEFD8" />
          <stop offset="70%" stop-color="#F7E2C7" />
          <stop offset="100%" stop-color="#EED3B4" />
        </linearGradient>

        <!-- Interior rosado de las orejitas y huellitas -->
        <linearGradient id="${uid}_pinkPad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#FFE0E6" />
          <stop offset="50%" stop-color="#FFBAC8" />
          <stop offset="100%" stop-color="#FFA8BA" />
        </linearGradient>

        <!-- Ojos anime morado/chocolate profundo con brillo cálido -->
        <linearGradient id="${uid}_eye" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#2D1527" />
          <stop offset="55%" stop-color="#4E2342" />
          <stop offset="100%" stop-color="#7C3560" />
        </linearGradient>

        <!-- Hocico blanco marfil -->
        <radialGradient id="${uid}_snout" cx="50%" cy="40%" r="65%">
          <stop offset="0%" stop-color="#FFFFFF" />
          <stop offset="85%" stop-color="#FFF7EC" />
          <stop offset="100%" stop-color="#F3E5D0" />
        </radialGradient>

        <!-- Traje quirúrgico (scrubs) celeste pastel -->
        <linearGradient id="${uid}_scrubs" x1="50" y1="75" x2="90" y2="140" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#BAE6FD" />
          <stop offset="50%" stop-color="#7DD3FC" />
          <stop offset="100%" stop-color="#38BDF8" />
        </linearGradient>

        <!-- Bata médica blanca con sombreado suave -->
        <linearGradient id="${uid}_coat" x1="30" y1="80" x2="110" y2="135" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stop-color="#FFFFFF" />
          <stop offset="70%" stop-color="#F8FAFC" />
          <stop offset="100%" stop-color="#E2E8F0" />
        </linearGradient>

        <!-- Corazón rojo/rosa para el estetoscopio y la tablilla -->
        <linearGradient id="${uid}_heart" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#FB7185" />
          <stop offset="100%" stop-color="#E11D48" />
        </linearGradient>

        <!-- Madera de la tablilla médica (clipboard) -->
        <linearGradient id="${uid}_clipboard" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stop-color="#EAD5BC" />
          <stop offset="100%" stop-color="#D4B490" />
        </linearGradient>
      </defs>

      <!-- Sombra suave en el piso -->
      <ellipse class="pulso-floor-shadow" cx="70" cy="148" rx="34" ry="5.5" fill="#475569" opacity="0.22" />

      <!-- RIG PRINCIPAL DE DR. OSO (Articulado, flota, camina y saluda) -->
      <g class="pulso-character-rig dr-oso-rig">

        <!-- 1. PATITAS INFERIORES CON CICLO DE CAMINATA / WADDLE -->
        <g class="pulso-foot-left dr-oso-leg-left">
          <!-- Pantalón quirúrgico celeste -->
          <rect x="49" y="125" width="15" height="13" rx="4" fill="url(#${uid}_scrubs)" stroke="#387A8E" stroke-width="2" />
          <!-- Patita redondeada de osito -->
          <path d="M 46 138 Q 56 134 66 138 L 66 146 L 46 146 Z" fill="url(#${uid}_fur)" stroke="#5C3E29" stroke-width="2.2" stroke-linejoin="round" />
          <!-- Almohadilla rosa de la patita -->
          <ellipse cx="56" cy="142" rx="4.5" ry="2.2" fill="url(#${uid}_pinkPad)" />
        </g>
        <g class="pulso-foot-right dr-oso-leg-right">
          <!-- Pantalón quirúrgico celeste -->
          <rect x="76" y="125" width="15" height="13" rx="4" fill="url(#${uid}_scrubs)" stroke="#387A8E" stroke-width="2" />
          <!-- Patita redondeada de osito -->
          <path d="M 74 138 Q 84 134 94 138 L 94 146 L 74 146 Z" fill="url(#${uid}_fur)" stroke="#5C3E29" stroke-width="2.2" stroke-linejoin="round" />
          <!-- Almohadilla rosa de la patita -->
          <ellipse cx="84" cy="142" rx="4.5" ry="2.2" fill="url(#${uid}_pinkPad)" />
        </g>

        <!-- 2. CUERPO, TRAJE QUIRÚRGICO Y BATA MÉDICA BLANCA -->
        <g class="pulso-torso-rig">
          <!-- Pecho con filipina / scrub V-neck celeste pastel -->
          <path d="M 52 82 L 88 82 L 86 128 L 54 128 Z" fill="url(#${uid}_scrubs)" stroke="#387A8E" stroke-width="2" />
          <!-- Cuello V-neck del scrub -->
          <polygon points="62,82 78,82 70,95" fill="#E0F2FE" stroke="#387A8E" stroke-width="1.8" />

          <!-- BATA MÉDICA BLANCA (Lado izquierdo) -->
          <path d="M 42 82 L 61 82 L 61 130 L 40 130 Z" fill="url(#${uid}_coat)" stroke="#5C3E29" stroke-width="2.4" stroke-linejoin="round" />
          <polygon points="50,82 61,82 61,102 51,94" fill="#F1F5F9" stroke="#5C3E29" stroke-width="1.8" stroke-linejoin="round" />
          <!-- Bolsillo izquierdo con pluma -->
          <rect x="44" y="112" width="11" height="11" rx="2" fill="#FFFFFF" stroke="#5C3E29" stroke-width="1.6" />
          <line x1="47" y1="108" x2="47" y2="114" stroke="#38BDF8" stroke-width="1.8" stroke-linecap="round" />

          <!-- BATA MÉDICA BLANCA (Lado derecho con gafete DR. OSO) -->
          <path d="M 79 82 L 98 82 L 100 130 L 79 130 Z" fill="url(#${uid}_coat)" stroke="#5C3E29" stroke-width="2.4" stroke-linejoin="round" />
          <polygon points="90,82 79,82 79,102 89,94" fill="#F1F5F9" stroke="#5C3E29" stroke-width="1.8" stroke-linejoin="round" />
          <!-- Gafete / ID Badge "DR. OSO" -->
          <g transform="translate(81, 105)">
            <rect x="0" y="0" width="14" height="9" rx="1.5" fill="#FFFFFF" stroke="#5C3E29" stroke-width="1.3" />
            <rect x="5" y="-3" width="4" height="3" rx="1" fill="#94A3B8" />
            <circle cx="3" cy="4.5" r="1.8" fill="#F472B6" />
            <line x1="6.5" y1="3" x2="12" y2="3" stroke="#5C3E29" stroke-width="1" />
            <line x1="6.5" y1="6" x2="11" y2="6" stroke="#94A3B8" stroke-width="0.8" />
          </g>

          <!-- ESTETOSCOPIO ROSA CON CORAZÓN LATIENDO -->
          <path d="M 58 84 Q 56 100 66 103 L 68 107" fill="none" stroke="#F472B6" stroke-width="2.6" stroke-linecap="round" />
          <path d="M 82 84 Q 84 100 74 103 L 72 107" fill="none" stroke="#F472B6" stroke-width="2.6" stroke-linecap="round" />
          <!-- Pieza pectoral en forma de corazón -->
          <g class="pulso-steth-heart" transform="translate(70, 109)">
            <path d="M 0 -2 C -4 -7, -9 -2, 0 5 C 9 -2, 4 -7, 0 -2 Z" fill="url(#${uid}_heart)" stroke="#BE123C" stroke-width="1.4" />
            <circle cx="-1.5" cy="-2.5" r="1" fill="#FFFFFF" opacity="0.8" />
          </g>
        </g>

        <!-- 3. BRAZO IZQUIERDO SOSTENIENDO LA TABLILLA MÉDICA (CLIPBOARD) -->
        <g class="pulso-arm-left dr-oso-arm-left">
          <!-- Manga de la bata blanca -->
          <path d="M 43 83 L 31 104 L 41 108 L 49 92 Z" fill="url(#${uid}_coat)" stroke="#5C3E29" stroke-width="2.4" stroke-linejoin="round" />
          <!-- Patita sosteniendo la tablilla -->
          <circle cx="36" cy="110" r="5.5" fill="url(#${uid}_fur)" stroke="#5C3E29" stroke-width="2" />
          
          <!-- Tablilla médica con hoja clínica y corazoncito -->
          <g class="dr-oso-clipboard" transform="rotate(-6 24 100) translate(12, 92)">
            <!-- Tablilla de madera -->
            <rect x="0" y="0" width="19" height="26" rx="2.5" fill="url(#${uid}_clipboard)" stroke="#8C532B" stroke-width="1.8" />
            <!-- Clip plateado superior -->
            <rect x="5.5" y="-2" width="8" height="4" rx="1.2" fill="#E2E8F0" stroke="#64748B" stroke-width="1.2" />
            <!-- Hoja de papel blanca -->
            <rect x="2" y="3" width="15" height="21" rx="1.5" fill="#FFFFFF" />
            <!-- Corazoncito sonriente en la hoja clínica -->
            <path d="M 9.5 8 C 7 5, 4 8, 9.5 12.5 C 15 8, 12 5, 9.5 8 Z" fill="#FB7185" />
            <circle cx="8" cy="8" r="0.6" fill="#3D2114" />
            <circle cx="11" cy="8" r="0.6" fill="#3D2114" />
            <path d="M 8.5 9.5 Q 9.5 10.5 10.5 9.5" fill="none" stroke="#3D2114" stroke-width="0.6" stroke-linecap="round" />
            <!-- Líneas de pulso / chequeos -->
            <line x1="4" y1="15" x2="15" y2="15" stroke="#38BDF8" stroke-width="1.2" stroke-linecap="round" />
            <line x1="4" y1="18" x2="13" y2="18" stroke="#34D399" stroke-width="1.2" stroke-linecap="round" />
            <line x1="4" y1="21" x2="10" y2="21" stroke="#F472B6" stroke-width="1.2" stroke-linecap="round" />
          </g>
        </g>

        <!-- 4. BRAZO DERECHO SALUDANDO CON HUELLITA ROSA (WAVING PAW) -->
        <g class="pulso-arm-right dr-oso-arm-right">
          <!-- Manga de la bata blanca -->
          <path d="M 97 83 L 110 102 L 102 107 L 91 92 Z" fill="url(#${uid}_coat)" stroke="#5C3E29" stroke-width="2.4" stroke-linejoin="round" />
          <!-- Patita gordita de osito saludando -->
          <g transform="translate(112, 104) rotate(-14)">
            <ellipse cx="0" cy="0" rx="7.5" ry="7" fill="url(#${uid}_fur)" stroke="#5C3E29" stroke-width="2.2" />
            <!-- Almohadilla rosa central de la patita -->
            <ellipse cx="0" cy="1" rx="4.2" ry="3.4" fill="url(#${uid}_pinkPad)" />
            <!-- 3 deditos / toe beans rositas -->
            <circle cx="-3.6" cy="-4.2" r="1.6" fill="url(#${uid}_pinkPad)" />
            <circle cx="0" cy="-5.2" r="1.7" fill="url(#${uid}_pinkPad)" />
            <circle cx="3.6" cy="-4.2" r="1.6" fill="url(#${uid}_pinkPad)" />
          </g>
          <!-- Ondas de saludo alegre (wave lines) -->
          <path class="dr-oso-wave-line w1" d="M 125 96 Q 128 102 125 108" fill="none" stroke="#F472B6" stroke-width="2" stroke-linecap="round" />
          <path class="dr-oso-wave-line w2" d="M 130 92 Q 134 102 130 112" fill="none" stroke="#F472B6" stroke-width="1.8" stroke-linecap="round" />
        </g>

        <!-- 5. CABECITA REDONDA KAWAII CON OREJITAS Y EXPRESIONES -->
        <g class="pulso-head-rig dr-oso-head-rig">
          
          <!-- Orejita izquierda -->
          <g class="dr-oso-ear-left">
            <circle cx="42" cy="38" r="13.5" fill="url(#${uid}_fur)" stroke="#5C3E29" stroke-width="2.4" />
            <circle cx="42" cy="39" r="7.5" fill="url(#${uid}_pinkPad)" />
          </g>

          <!-- Orejita derecha -->
          <g class="dr-oso-ear-right">
            <circle cx="98" cy="38" r="13.5" fill="url(#${uid}_fur)" stroke="#5C3E29" stroke-width="2.4" />
            <circle cx="98" cy="39" r="7.5" fill="url(#${uid}_pinkPad)" />
          </g>

          <!-- Forma principal de la cabeza esponjosa -->
          <ellipse cx="70" cy="57" rx="33" ry="29" fill="url(#${uid}_fur)" stroke="#5C3E29" stroke-width="2.6" />

          <!-- Mechoncito de pelito fluffy en la frente -->
          <path d="M 64 29 Q 69 22 73 27 Q 76 23 78 28 Q 72 26 64 29 Z" fill="url(#${uid}_fur)" stroke="#5C3E29" stroke-width="2" stroke-linejoin="round" />

          <!-- Cejitas expresivas -->
          ${browsContent}

          <!-- Ojos anime kawaii grandes con destellos -->
          ${eyesContent}

          <!-- Chapitas sonrosadas (blush ovals) con rayitas kawaii -->
          <ellipse cx="44" cy="62" rx="6.5" ry="3.8" fill="#FFA8B6" opacity="0.82" />
          <line x1="42" y1="61" x2="44" y2="64" stroke="#FF6B8B" stroke-width="1.4" stroke-linecap="round" />
          <line x1="45" y1="61" x2="47" y2="64" stroke="#FF6B8B" stroke-width="1.4" stroke-linecap="round" />

          <ellipse cx="96" cy="62" rx="6.5" ry="3.8" fill="#FFA8B6" opacity="0.82" />
          <line x1="94" y1="61" x2="96" y2="64" stroke="#FF6B8B" stroke-width="1.4" stroke-linecap="round" />
          <line x1="97" y1="61" x2="99" y2="64" stroke="#FF6B8B" stroke-width="1.4" stroke-linecap="round" />

          <!-- Hocico blanco marfil ovalado -->
          <ellipse cx="70" cy="63" rx="13" ry="9.5" fill="url(#${uid}_snout)" stroke="#5C3E29" stroke-width="1.8" />

          <!-- Nariz de osito chocolate -->
          <ellipse cx="70" cy="59" rx="3.8" ry="2.8" fill="#3D2114" />
          <circle cx="68.8" cy="58" r="0.9" fill="#FFFFFF" />

          <!-- Boquita sonriente y lengüita -->
          ${mouthContent}

          <!-- Chispas, bombilla o corazoncitos según el estado -->
          ${extraOverlay}

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
