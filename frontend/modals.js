/**
 * modals.js — MedicAItion v3.0
 * =========================================
 * Controladores de modales de la interfaz de "Nueva Consulta":
 *   1. Modal "Crear Evento Clínico"
 *   2. Modal "Asociar Nota y Recetas como consulta a Evento Clínico"
 *   3. Modal "Registrar Paciente" (Gestor de Pacientes)
 *
 * Los modales usan el sistema de overlay genérico (openOverlay/closeOverlay).
 * Todas las llamadas API usan JSON en el body.
 */

// ─────────────────────────────────────────────────────────────────
// OVERLAY GENÉRICO (heredado del sistema previo, ahora modular)
// ─────────────────────────────────────────────────────────────────

const _overlayLegacyStack = [];

function openOverlay(contentHtml, options = {}) {
  const overlay = document.getElementById('app-overlay');
  const content = document.getElementById('app-overlay-content');

  content.className = 'app-overlay-content';
  if (options.wide) content.classList.add('wide');
  if (options.full) content.classList.add('full');

  content.innerHTML = contentHtml;
  overlay.classList.add('open');
  _overlayLegacyStack.push({ html: contentHtml, options });
}

function closeOverlay() {
  const overlay = document.getElementById('app-overlay');
  overlay.classList.remove('open');
  _overlayLegacyStack.length = 0;
}

function popOverlay() {
  if (_overlayLegacyStack.length > 1) {
    _overlayLegacyStack.pop();
    const prev = _overlayLegacyStack[_overlayLegacyStack.length - 1];
    const content = document.getElementById('app-overlay-content');
    content.className = 'app-overlay-content';
    if (prev.options.wide) content.classList.add('wide');
    if (prev.options.full) content.classList.add('full');
    content.innerHTML = prev.html;
  } else {
    closeOverlay();
  }
}

// Cerrar al hacer click en el fondo oscuro
document.addEventListener('click', (e) => {
  if (e.target.id === 'app-overlay') {
    // Si el OverlaySystem está activo, lo cerramos; si no, cerramos el legacy
    if (window.OverlaySystem && document.getElementById('app-overlay').classList.contains('open')) {
      // Solo cerrar si NO hay un overlay del OverlaySystem activo
      closeOverlay();
    }
  }
});


// ─────────────────────────────────────────────────────────────────
// MODAL 1: CREAR EVENTO CLÍNICO
// ─────────────────────────────────────────────────────────────────

async function openCreateEventModal() {
  const curp = document.getElementById('curp-input').value.trim();

  if (!curp) {
    showToast('Ingresa el CURP o ID del paciente primero', 'error');
    document.getElementById('curp-input').focus();
    return;
  }

  // Verificar si el paciente está registrado
  try {
    const res = await fetch(`${API}/api/patients/${encodeURIComponent(curp)}/exists`);
    if (!res.ok) throw new Error('Error al verificar');
    const { exists } = await res.json();
    if (!exists) {
      showToast('El paciente no está registrado. Regístralo primero en "Pacientes".', 'error');
      return;
    }
  } catch (err) {
    showToast('Error al verificar el paciente: ' + err.message, 'error');
    return;
  }

  // Cargar info del paciente para mostrar en la modal
  let nombrePaciente = curp;
  try {
    const res = await fetch(`${API}/api/patients/${encodeURIComponent(curp)}`);
    if (res.ok) {
      const p = await res.json();
      nombrePaciente = p.nombre || p.nombre_completo || curp;
    }
  } catch { /* silent */ }

  const now = new Date();
  const datetimeLocal = now.toISOString().slice(0, 16); // "YYYY-MM-DDTHH:mm"

  const html = `
    <div class="overlay-header">
      <h3>Crear Evento Clínico</h3>
      <button class="overlay-close-btn" onclick="closeOverlay()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>

    <div class="overlay-info-block">
      <div class="info-label">PACIENTE ASOCIADO</div>
      <div class="info-value"><strong>${_modalEsc(nombrePaciente)}</strong></div>
      <div class="info-value" style="font-size:11px; opacity:0.7;">ID del Paciente: ${_modalEsc(curp)}</div>
    </div>

    <div class="overlay-field">
      <label>Nombre del evento</label>
      <input type="text" id="modal-event-name" class="input-field" placeholder="Ingresa el nombre del evento clínico" autofocus />
    </div>

    <div class="overlay-field">
      <label>Doctor que realizó el evento (*obligatorio)</label>
      <input type="text" id="modal-event-doctor" class="input-field" placeholder="Selecciona o ingresa el nombre del doctor" />
    </div>

    <div class="overlay-field">
      <label>Fecha y hora de creación</label>
      <input type="datetime-local" id="modal-event-datetime" class="input-field" value="${datetimeLocal}" />
    </div>

    <div class="overlay-actions">
      <button class="overlay-btn-cancel" onclick="closeOverlay()">Cancelar</button>
      <button class="overlay-btn-confirm" id="modal-create-event-btn" onclick="handleCreateEvent('${_modalEsc(curp)}')">Crear</button>
    </div>
  `;

  openOverlay(html);
}


async function handleCreateEvent(curp) {
  const name     = document.getElementById('modal-event-name')?.value.trim();
  const doctor   = document.getElementById('modal-event-doctor')?.value.trim();
  const datetime = document.getElementById('modal-event-datetime')?.value;
  const btn      = document.getElementById('modal-create-event-btn');

  if (!name)   return showToast('Ingresa el nombre del evento', 'error');
  if (!doctor) return showToast('Ingresa el nombre del doctor', 'error');

  if (btn) { btn.disabled = true; btn.textContent = 'Creando...'; }

  try {
    const res = await fetch(`${API}/api/patients/${encodeURIComponent(curp)}/events`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        nombre_evento: name,
        doctor_creador: doctor,
        fecha_hora_creacion: datetime ? new Date(datetime).toISOString() : null,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Error desconocido' }));
      throw new Error(err.detail || 'Error al crear el evento');
    }

    const evento = await res.json();
    updateEventStatus(evento.id, evento.nombre_evento);
    closeOverlay();
    showToast(`Evento Clínico "${name}" creado`, 'success');
  } catch (err) {
    showToast('Error: ' + err.message, 'error');
    if (btn) { btn.disabled = false; btn.textContent = 'Crear'; }
  }
}


// ─────────────────────────────────────────────────────────────────
// MODAL 2: ASOCIAR NOTA Y RECETA A EVENTO CLÍNICO
// ─────────────────────────────────────────────────────────────────

async function openAssociateNoteModal() {
  const curp = document.getElementById('curp-input').value.trim();

  if (!AppState.lastProcessedRecord) {
    showToast('Primero genera las notas médicas', 'error');
    return;
  }

  // Cargar eventos del paciente para mostrar en el select
  let eventosOptions = '';
  if (curp) {
    try {
      const res = await fetch(`${API}/api/patients/${encodeURIComponent(curp)}/events`);
      if (res.ok) {
        const eventos = await res.json();
        if (eventos.length === 0) {
          eventosOptions = '<option value="">Sin eventos — crea uno primero</option>';
        } else {
          eventosOptions = eventos.map(e =>
            `<option value="${_modalEsc(e.id)}" ${AppState.currentEventId === e.id ? 'selected' : ''}>${_modalEsc(e.nombre_evento)}</option>`
          ).join('');
        }
      }
    } catch { eventosOptions = '<option value="">Error al cargar eventos</option>'; }
  }

  const now = new Date();
  const datetimeLocal = now.toISOString().slice(0, 16);

  const seg = AppState.lastProcessedRecord?.seguridad_clinica || {};
  const critAlerts = (seg.alertas_medicamentos || []).filter(a => a.severidad === 'CRITICA');
  const safetyBlockHtml = seg.bloqueo_seguridad ? `
    <div id="modal-safety-override-box" style="background:#fef2f2;border:1.5px solid #ef4444;border-radius:12px;padding:12px 14px;margin-bottom:14px;color:#7f1d1d;">
      <div style="font-weight:700;font-size:13px;margin-bottom:6px;display:flex;align-items:center;gap:6px;">
        ⛔ Alerta Crítica de Seguridad Farmacológica
      </div>
      <ul style="margin:0 0 8px;padding-left:18px;font-size:12px;line-height:1.45;">
        ${critAlerts.map(a => `<li><strong>${_modalEsc(a.medicamento)}:</strong> ${_modalEsc(a.titulo)}</li>`).join('')}
      </ul>
      <label style="display:flex;align-items:flex-start;gap:8px;font-size:12px;font-weight:600;cursor:pointer;margin-bottom:6px;">
        <input type="checkbox" id="modal-safety-confirm-check" style="margin-top:2px;" />
        <span>Confirmo que evalué el riesgo clínico y autorizo el registro bajo justificación médica explícita:</span>
      </label>
      <input type="text" id="modal-safety-justification" class="input-field" style="background:#fff;color:#0f172a;border-color:#fca5a5;" placeholder="Ej. Se ajustará alternativa segura / beneficio supera riesgo..." />
    </div>
  ` : '';

  const html = `
    <div class="overlay-header">
      <h3>Asociar Nota y Recetas como consulta a Evento Clínico</h3>
      <button class="overlay-close-btn" onclick="closeOverlay()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>

    ${safetyBlockHtml}

    <div class="overlay-field">
      <label>Elegir evento clínico</label>
      <select id="modal-assoc-event" class="input-field">
        <option value="">Selecciona un evento clínico</option>
        ${eventosOptions}
      </select>
    </div>

    <div class="overlay-field">
      <label>Descripción del evento (opcional pero recomendable)</label>
      <textarea id="modal-assoc-desc" class="textarea-field" rows="3"
        placeholder="Describe brevemente el motivo de la consulta, evolución o hallazgos relevantes..."></textarea>
    </div>

    <div class="overlay-field">
      <label>Doctor que realizó la consulta (*obligatorio)</label>
      <input type="text" id="modal-assoc-doctor" class="input-field" value="${_modalEsc(AppState.operatorProfile?.full_name || 'Dr. Roberto Morales')}" placeholder="Selecciona o ingresa el nombre del doctor" />
    </div>

    <div class="overlay-field">
      <label>Cédula Profesional (Sello NOM-004)</label>
      <input type="text" id="modal-assoc-cedula" class="input-field" value="${_modalEsc(AppState.operatorProfile?.cedula_profesional || '')}" placeholder="CED-9482710" />
    </div>

    <div class="overlay-field">
      <label>Fecha y hora (*obligatorio)</label>
      <input type="datetime-local" id="modal-assoc-datetime" class="input-field" value="${datetimeLocal}" />
    </div>

    <button class="btn-preview-nota" onclick="_previewNotaModal()">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
      Previsualizar nota y receta
    </button>

    <div class="overlay-actions">
      <button class="overlay-btn-cancel" onclick="closeOverlay()">Cancelar</button>
      <button class="overlay-btn-confirm" id="modal-assoc-btn" onclick="handleAssociateNote()">Crear Consulta</button>
    </div>
  `;

  openOverlay(html);
}


async function handleAssociateNote() {
  const eventoId = document.getElementById('modal-assoc-event')?.value;
  const desc     = document.getElementById('modal-assoc-desc')?.value.trim();
  const doctor   = document.getElementById('modal-assoc-doctor')?.value.trim();
  const cedula   = document.getElementById('modal-assoc-cedula')?.value.trim();
  const datetime = document.getElementById('modal-assoc-datetime')?.value;
  const btn      = document.getElementById('modal-assoc-btn');

  if (!eventoId) return showToast('Selecciona un evento clínico', 'error');
  if (!doctor)   return showToast('Ingresa el nombre del doctor', 'error');

  const record = AppState.lastProcessedRecord;
  if (!record)   return showToast('No hay notas para asociar — procesa el caso primero', 'error');

  let justificacion = null;
  if (record.seguridad_clinica?.bloqueo_seguridad) {
    const checked = document.getElementById('modal-safety-confirm-check')?.checked;
    const reason = document.getElementById('modal-safety-justification')?.value.trim();
    if (!checked || !reason) {
      return showToast('⚠️ Alerta crítica activa: marca la confirmación e ingresa la justificación médica', 'error');
    }
    justificacion = reason;
  }

  if (btn) { btn.disabled = true; btn.textContent = 'Guardando...'; }

  try {
    // Construir el payload de la consulta
    const payload = {
      evento_id:     eventoId,
      doctor_nombre: doctor,
      cedula_profesional: cedula || AppState.operatorProfile?.cedula_profesional || null,
      fecha_hora:    datetime ? new Date(datetime).toISOString() : new Date().toISOString(),
      resumen_doctor: desc || null,
      justificacion_seguridad: justificacion,
      nota_medica:   record.nota_clinica || {},
      receta: {
        medicamentos:  record.medicamentos || record.entidades_extraidas?.medicamentos || [],
        instrucciones: record.receta_paciente || record.plan_tratamiento || '',
      },
      entidades: {
        codigos_cie10:          record.codigos_cie10 || {},
        sintomas_referidos:     record.entidades_extraidas?.sintomas_referidos || [],
        diagnosticos_tentativos: record.entidades_extraidas?.diagnosticos_tentativos || [],
        signos_vitales:         record.entidades_extraidas?.signos_vitales || [],
        diagnostico_diferencial: record.diagnostico_diferencial || [],
      },
      texto_original: record.texto_original || '',
    };

    const res = await fetch(`${API}/api/consultations/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Error desconocido' }));
      const msg = typeof err.detail === 'object' ? (err.detail.message || JSON.stringify(err.detail)) : err.detail;
      throw new Error(msg || 'Error al guardar la consulta');
    }

    const savedConsulta = await res.json().catch(() => null);
    if (savedConsulta && savedConsulta.id) {
      const qrBox = document.getElementById('receta-qr-box');
      const verifEl = document.getElementById('receta-verif-code');
      if (verifEl) verifEl.textContent = `MED-${savedConsulta.id.substring(0, 8).toUpperCase()}`;
      if (qrBox) {
        qrBox.innerHTML = `<img src="${API}/api/consultations/${encodeURIComponent(savedConsulta.id)}/receta/qr" alt="QR Verificación" style="width:76px;height:76px;" />`;
      }
    }

    closeOverlay();
    showToast('✅ Consulta guardada exitosamente en el evento clínico', 'success');

    // Marcar cita vinculada como Atendida y refrescar tablero clínico
    if (AppState.activeAppointmentId && !String(AppState.activeAppointmentId).startsWith('appt-')) {
      if (typeof updateAppointmentField === 'function') {
        updateAppointmentField(AppState.activeAppointmentId, { status: 'Atendida' });
      }
      AppState.activeAppointmentId = null;
    }
    if (typeof refreshDashboard === 'function') refreshDashboard();

    // Limpiar el estado del borrador en memoria
    AppState.lastProcessedRecord = null;
    document.getElementById('btn-associate-note').style.display = 'none';

  } catch (err) {
    showToast('Error: ' + err.message, 'error');
    if (btn) { btn.disabled = false; btn.textContent = 'Crear Consulta'; }
  }
}


function _previewNotaModal() {
  const record = AppState.lastProcessedRecord;
  if (!record) return showToast('Sin notas para previsualizar', 'info');

  const nota = record.nota_clinica || {};
  const meds = record.medicamentos || record.entidades_extraidas?.medicamentos || [];

  const previewHtml = `
    <div class="overlay-header">
      <button class="overlay-back-btn" onclick="popOverlay()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
      <h3>Previsualización — Nota y Receta</h3>
    </div>

    <div style="padding: 16px; overflow-y: auto; max-height: 60vh;">
      <h4 style="color: var(--accent-cyan); margin-bottom: 8px;">Nota Médica (NOM-004)</h4>
      <div class="preview-section"><strong>Motivo:</strong> ${_modalEsc(nota.motivo_consulta || '—')}</div>
      <div class="preview-section"><strong>Evolución:</strong> ${_modalEsc(nota.evolucion_padecimiento || '—')}</div>
      <div class="preview-section"><strong>Exploración:</strong> ${_modalEsc(nota.exploracion_fisica || '—')}</div>
      <div class="preview-section"><strong>Diagnóstico:</strong> ${_modalEsc(nota.diagnostico_integral || '—')}</div>
      <div class="preview-section"><strong>Plan:</strong> ${_modalEsc(nota.plan_tratamiento || '—')}</div>

      <h4 style="color: var(--accent-cyan); margin-top: 16px; margin-bottom: 8px;">Receta Médica</h4>
      ${meds.length > 0
        ? meds.map(m => `<div class="preview-section">💊 <strong>${_modalEsc(m.nombre)}</strong> — ${_modalEsc(m.dosis || '')} ${_modalEsc(m.via || '')} ${_modalEsc(m.periodicidad || '')}</div>`).join('')
        : '<div class="preview-section text-muted">Sin medicamentos prescritos</div>'}
    </div>
  `;

  // Push sobre el overlay actual (sin cerrar el de asociar nota)
  const content = document.getElementById('app-overlay-content');
  _overlayLegacyStack.push({ html: content.innerHTML, options: {} });
  content.innerHTML = previewHtml;
}


// ─────────────────────────────────────────────────────────────────
// MODAL 3: REGISTRAR PACIENTE
// ─────────────────────────────────────────────────────────────────

function openRegisterPatientModal() {
  const html = `
    <div class="overlay-header">
      <h3>Registrar Nuevo Paciente</h3>
      <button class="overlay-close-btn" onclick="closeOverlay()">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>

    <div class="register-form-scroll">

      <div class="register-section-title">Datos Obligatorios</div>
      <div class="register-grid">
        <div class="overlay-field">
          <label>Primer Apellido *</label>
          <input type="text" id="reg-primer-apellido" class="input-field" placeholder="Apellido paterno" />
        </div>
        <div class="overlay-field">
          <label>Segundo Apellido</label>
          <input type="text" id="reg-segundo-apellido" class="input-field" placeholder="Apellido materno" />
        </div>
        <div class="overlay-field">
          <label>Nombre(s) *</label>
          <input type="text" id="reg-nombres" class="input-field" placeholder="Nombres completos" />
        </div>
        <div class="overlay-field">
          <label>Fecha de Nacimiento *</label>
          <input type="date" id="reg-fecha-nac" class="input-field" />
        </div>
        <div class="overlay-field">
          <label>Sexo *</label>
          <select id="reg-sexo" class="input-field">
            <option value="">Seleccionar...</option>
            <option value="M">Masculino</option>
            <option value="F">Femenino</option>
          </select>
        </div>
        <div class="overlay-field">
          <label>CURP *</label>
          <input type="text" id="reg-curp" class="input-field" placeholder="18 caracteres" maxlength="18" style="text-transform:uppercase" />
        </div>
        <div class="overlay-field">
          <label>Dirección de casa *</label>
          <input type="text" id="reg-ubicacion" class="input-field" placeholder="Calle, Colonia, Ciudad" />
        </div>
        <div class="overlay-field">
          <label>No. Expediente Hospital (Folio)</label>
          <input type="text" id="reg-folio" class="input-field" placeholder="Pendiente de asignar" />
        </div>
      </div>

      <div class="register-section-title">Identificadores</div>
      <div class="register-grid">
        <div class="overlay-field">
          <label>RFC</label>
          <input type="text" id="reg-rfc" class="input-field" placeholder="RFC (opcional)" />
        </div>
        <div class="overlay-field">
          <label>NSS (Número de Seguro Social)</label>
          <input type="text" id="reg-nss" class="input-field" placeholder="NSS (opcional)" />
        </div>
        <div class="overlay-field">
          <label>No. Expediente Externo</label>
          <input type="text" id="reg-exp-ext" class="input-field" placeholder="Opcional" />
        </div>
        <div class="overlay-field">
          <label>Nacionalidad</label>
          <input type="text" id="reg-nacionalidad" class="input-field" value="Mexicana" />
        </div>
        <div class="overlay-field">
          <label>Lugar de Nacimiento</label>
          <input type="text" id="reg-lugar-nac" class="input-field" placeholder="Ciudad, Estado, País" />
        </div>
      </div>

      <div class="register-section-title">Perfil Social</div>
      <div class="register-grid">
        <div class="overlay-field">
          <label>Estado Civil</label>
          <select id="reg-estado-civil" class="input-field">
            <option value="">Seleccionar...</option>
            <option>Soltero/a</option><option>Casado/a</option>
            <option>Divorciado/a</option><option>Viudo/a</option><option>Unión libre</option>
          </select>
        </div>
        <div class="overlay-field">
          <label>Ocupación</label>
          <input type="text" id="reg-ocupacion" class="input-field" placeholder="Profesión u oficio" />
        </div>
        <div class="overlay-field">
          <label>Tipo de Paciente</label>
          <input type="text" id="reg-tipo-paciente" class="input-field" placeholder="Ej: Consulta externa, Urgencias..." />
        </div>
        <div class="overlay-field">
          <label>Programa Médico/Social</label>
          <input type="text" id="reg-programa" class="input-field" placeholder="Ej: IMSS, Seguro Popular..." />
        </div>
      </div>

      <div class="register-section-title">Comunicación</div>
      <div class="register-grid">
        <div class="overlay-field">
          <label>Teléfono local</label>
          <input type="tel" id="reg-tel-local" class="input-field" placeholder="999-000-0000" />
        </div>
        <div class="overlay-field">
          <label>Celular (con prefijo)</label>
          <input type="tel" id="reg-celular" class="input-field" placeholder="+52 999 000 0000" />
        </div>
        <div class="overlay-field">
          <label>Correo electrónico</label>
          <input type="email" id="reg-email" class="input-field" placeholder="correo@ejemplo.com" />
        </div>
      </div>

      <div class="register-section-title">Contacto de Emergencia</div>
      <div class="register-grid">
        <div class="overlay-field">
          <label>Nombre del familiar</label>
          <input type="text" id="reg-contacto-nombre" class="input-field" placeholder="Nombre completo del familiar" />
        </div>
        <div class="overlay-field">
          <label>Teléfono del familiar</label>
          <input type="tel" id="reg-contacto-tel" class="input-field" placeholder="+52 999 000 0000" />
        </div>
      </div>

      <div class="register-section-title">Seguros y Anotaciones</div>
      <div class="overlay-field">
        <label>Aseguradoras</label>
        <input type="text" id="reg-aseguradoras" class="input-field" placeholder="Ej: IMSS, Seguros Atlas (separadas por comas)" />
      </div>
      <div class="overlay-field">
        <label>Anotaciones Generales</label>
        <textarea id="reg-anotaciones" class="textarea-field" rows="3" placeholder="Observaciones generales del paciente..."></textarea>
      </div>

    </div>

    <div class="overlay-actions">
      <button class="overlay-btn-cancel" onclick="closeOverlay()">Cancelar</button>
      <button class="overlay-btn-confirm" id="reg-submit-btn" onclick="handleRegisterPatient()">Registrar Paciente</button>
    </div>
  `;

  openOverlay(html, { wide: true });
}


async function handleRegisterPatient() {
  const btn = document.getElementById('reg-submit-btn');

  const curp = document.getElementById('reg-curp')?.value.trim().toUpperCase();
  const nombres = document.getElementById('reg-nombres')?.value.trim();
  const primerApellido = document.getElementById('reg-primer-apellido')?.value.trim();
  const ubicacion = document.getElementById('reg-ubicacion')?.value.trim();

  if (!primerApellido) return showToast('El primer apellido es obligatorio', 'error');
  if (!nombres)        return showToast('El nombre es obligatorio', 'error');
  if (!curp)           return showToast('El CURP/ID es obligatorio', 'error');
  if (!ubicacion)      return showToast('La dirección de casa es obligatoria', 'error');

  if (btn) { btn.disabled = true; btn.textContent = 'Registrando...'; }

  const payload = {
    curp,
    primer_apellido:           primerApellido,
    segundo_apellido:          document.getElementById('reg-segundo-apellido')?.value.trim() || '',
    nombres,
    fecha_nacimiento:          document.getElementById('reg-fecha-nac')?.value || null,
    sexo:                      document.getElementById('reg-sexo')?.value || null,
    folio_hospital:            document.getElementById('reg-folio')?.value.trim() || null,
    ubicacion_casa:            ubicacion,
    rfc:                       document.getElementById('reg-rfc')?.value.trim() || null,
    nss:                       document.getElementById('reg-nss')?.value.trim() || null,
    expediente_externo:        document.getElementById('reg-exp-ext')?.value.trim() || null,
    nacionalidad:              document.getElementById('reg-nacionalidad')?.value.trim() || 'Mexicana',
    lugar_nacimiento:          document.getElementById('reg-lugar-nac')?.value.trim() || null,
    estado_civil:              document.getElementById('reg-estado-civil')?.value || null,
    ocupacion:                 document.getElementById('reg-ocupacion')?.value.trim() || null,
    tipo_paciente:             document.getElementById('reg-tipo-paciente')?.value.trim() || null,
    programa_medico:           document.getElementById('reg-programa')?.value.trim() || null,
    telefono_local:            document.getElementById('reg-tel-local')?.value.trim() || null,
    celular:                   document.getElementById('reg-celular')?.value.trim() || null,
    email:                     document.getElementById('reg-email')?.value.trim() || null,
    contacto_emergencia_nombre: document.getElementById('reg-contacto-nombre')?.value.trim() || null,
    contacto_emergencia_tel:   document.getElementById('reg-contacto-tel')?.value.trim() || null,
    aseguradoras:              (document.getElementById('reg-aseguradoras')?.value || '')
                                 .split(',')
                                 .map(s => s.trim())
                                 .filter(Boolean),
    anotaciones_generales:     document.getElementById('reg-anotaciones')?.value.trim() || null,
  };

  try {
    const res = await fetch(`${API}/api/patients/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Error desconocido' }));
      throw new Error(err.detail || 'Error al registrar el paciente');
    }

    closeOverlay();
    showToast(`✅ Paciente ${nombres} ${primerApellido} registrado`, 'success');
    // Refrescar la lista de pacientes
    if (typeof loadPatients === 'function') loadPatients();

  } catch (err) {
    showToast('Error: ' + err.message, 'error');
    if (btn) { btn.disabled = false; btn.textContent = 'Registrar Paciente'; }
  }
}


// ─────────────────────────────────────────────────────────────────
// HELPERS
// ─────────────────────────────────────────────────────────────────

function _modalEsc(str) {
  if (!str) return '';
  const d = document.createElement('div');
  d.textContent = String(str);
  return d.innerHTML;
}

// Exportar al scope global para que el HTML inline pueda acceder
window.openOverlay            = openOverlay;
window.closeOverlay           = closeOverlay;
window.popOverlay             = popOverlay;
window.openCreateEventModal   = openCreateEventModal;
window.handleCreateEvent      = handleCreateEvent;
window.openAssociateNoteModal = openAssociateNoteModal;
window.handleAssociateNote    = handleAssociateNote;
window.openRegisterPatientModal = openRegisterPatientModal;
window.handleRegisterPatient  = handleRegisterPatient;
