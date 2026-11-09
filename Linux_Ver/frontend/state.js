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

// Exportar global para que todos los scripts inline accedan
window.AppState = AppState;
