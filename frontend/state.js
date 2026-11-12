/**
 * state.js — MedicAItion v3.0
 * ========================================
 * Estado global centralizado de la aplicación.
 * Todos los módulos leen y escriben aquí; evitamos variables sueltas por archivo.
 */

const API = '';  // Same-origin global API path

const AppState = {
  // ── Modo de entrada ─────────────────────────────────────────────
  currentMode: 'audio',        // 'audio' | 'text'
  mainTab: 'dashboard',        // 'dashboard' | 'consulta' | 'expedientes'
  llmMode: 'auto',             // 'auto' | 'claude' | 'local'

  // ── Grabación de audio ─────────────────────────────────────────
  mediaRecorder: null,
  audioChunks: [],
  isRecording: false,
  timerInterval: null,
  timerSeconds: 0,
  recordedBlob: null,

  // ── Resultado de procesamiento (borrador en memoria) ──────────
  currentResultTab: 'original', // 'original' | 'nota' | 'receta'
  lastProcessedRecord: null,    // El JSON completo devuelto por el pipeline
  lastProcessedCurp: null,

  // ── Evento Clínico activo (en sesión de Nueva Consulta) ──────
  currentEventId: null,
  currentEventName: null,

  // ── Gestor de Pacientes ────────────────────────────────────────
  selectedPatientCurp: null,
  currentPatientEvents: [],
  selectedConsultationId: null,

  // ── Perfil profesional y RBAC (Sprint 4) ───────────────────────
  operatorProfile: {
    role: 'Médico',
    full_name: 'Dr. Roberto Morales',
    cedula_profesional: 'CED-9482710',
    specialty: 'Medicina General / Urgencias',
    clues_institucion: 'YUC-CR-001',
  },

  // ── Helpers ────────────────────────────────────────────────────
  reset() {
    this.lastProcessedRecord = null;
    this.lastProcessedCurp = null;
    this.currentEventId = null;
    this.currentEventName = null;
    this.recordedBlob = null;
    this.audioChunks = [];
  }
};

// Inyectar encabezados de rol y cédula en todas las llamadas a /api/
(function installRoleHeaderInterceptor() {
  if (typeof window === 'undefined' || !window.fetch || window._medicRoleFetchPatched) return;
  const origFetch = window.fetch.bind(window);
  window._medicRoleFetchPatched = true;
  window.fetch = function(input, init) {
    const url = typeof input === 'string' ? input : (input && input.url) || '';
    if (url.startsWith('/api/') || url.includes('/api/')) {
      const op = (window.AppState && window.AppState.operatorProfile) || {};
      const opts = Object.assign({}, init || {});
      const headers = new Headers(opts.headers || (typeof input !== 'string' && input.headers) || {});
      if (!headers.has('X-Operator-Role') && op.role) headers.set('X-Operator-Role', encodeURIComponent(op.role));
      if (!headers.has('X-Operator-Name') && op.full_name) headers.set('X-Operator-Name', encodeURIComponent(op.full_name));
      if (!headers.has('X-Operator-Cedula') && op.cedula_profesional) headers.set('X-Operator-Cedula', encodeURIComponent(op.cedula_profesional));
      opts.headers = headers;
      return origFetch(input, opts);
    }
    return origFetch(input, init);
  };
})();

// Exportar global para que todos los scripts inline accedan
window.AppState = AppState;
