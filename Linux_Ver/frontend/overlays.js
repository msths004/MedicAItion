/**
 * overlays.js — MedicAItion v3.0
 * =========================================
 * Sistema de navegación por overlay como stack.
 *
 * Flujo de navegación:
 *   Lista de Pacientes → Perfil del Paciente → Historial (Eventos Clínicos)
 *   → Consultas de un Evento → Detalle de Consulta
 *
 * Funciona con UN solo overlay opaco. Las vistas se apilan internamente
 * como un stack de navegación con transiciones. El botón "Atrás" hace pop
 * del stack sin cerrar el overlay.
 *
 * API pública:
 *   overlays.open(viewName, data)   — Abre overlay o navega a nueva vista
 *   overlays.push(viewName, data)   — Empuja nueva vista sobre la actual
 *   overlays.pop()                  — Regresa a la vista anterior
 *   overlays.close()                — Cierra el overlay completamente
 */

const OverlaySystem = (() => {
  const API = '';
  const stack = [];  // [{ viewName, data, html }, ...]

  // ── VISTAS DISPONIBLES ─────────────────────────────────────────────────────
  const views = {
    'patient-profile':      renderPatientProfile,
    'edit-patient-profile': renderEditPatientProfile,
    'patient-events':       renderPatientEvents,
    'event-consultas':      renderEventConsultas,
  };

  // ── CORE ENGINE ────────────────────────────────────────────────────────────

  async function open(viewName, data = {}) {
    stack.length = 0;  // Reset del stack
    await _push(viewName, data);
    _showOverlay();
  }

  async function push(viewName, data = {}) {
    await _push(viewName, data);
    _showOverlay();
  }

  function pop() {
    if (stack.length > 1) {
      stack.pop();
      _renderCurrentView(true); // animate backwards
    } else {
      close();
    }
  }

  function close() {
    const overlay = document.getElementById('app-overlay');
    overlay.classList.remove('open');
    stack.length = 0;
  }

  async function _push(viewName, data) {
    const renderFn = views[viewName];
    if (!renderFn) {
      console.error(`[Overlay] Vista desconocida: ${viewName}`);
      return;
    }
    // Show loading while fetching data
    _setLoading(true);
    try {
      const html = await renderFn(data);
      stack.push({ viewName, data, html });
      _renderCurrentView(false);
    } catch (err) {
      console.error(`[Overlay] Error al renderizar ${viewName}:`, err);
      window.showToast?.('Error al cargar vista', 'error');
    } finally {
      _setLoading(false);
    }
  }

  function _showOverlay() {
    const overlay = document.getElementById('app-overlay');
    overlay.classList.add('open');
  }

  function _setLoading(on) {
    const content = document.getElementById('app-overlay-content');
    if (!content) return;
    if (on && stack.length === 0) {
      content.innerHTML = '<div class="overlay-loading"><div class="spinner"></div></div>';
    }
  }

  function _renderCurrentView(backwards = false) {
    const frame = stack[stack.length - 1];
    if (!frame) return;
    const content = document.getElementById('app-overlay-content');
    content.className = 'app-overlay-content full';
    content.classList.add(backwards ? 'slide-in-left' : 'slide-in-right');
    content.innerHTML = frame.html;
    // Remove animation class after transition
    setTimeout(() => content.classList.remove('slide-in-left', 'slide-in-right'), 350);
  }

  // ── RENDER: PERFIL DEL PACIENTE ────────────────────────────────────────────

  async function renderPatientProfile(data) {
    const curp = data.curp;
    const res = await fetch(`${API}/api/patients/${encodeURIComponent(curp)}`);
    if (!res.ok) throw new Error('No se pudo cargar el perfil');
    const p = await res.json();

    const bmi = p.bmi ? `${p.bmi} kg/m²` : '—';
    const edad = p.edad != null ? `${p.edad} años` : '—';

    // Cargar el evento más reciente para el badge "Problema más reciente"
    let problemaReciente = '—';
    try {
      const evRes = await fetch(`${API}/api/patients/${encodeURIComponent(curp)}/events`);
      if (evRes.ok) {
        const eventos = await evRes.json();
        if (eventos.length > 0) {
          // Los eventos ya vienen ordenados por updated_at desc
          problemaReciente = eventos[0].nombre_evento;
        }
      }
    } catch { /* silent */ }

    // Fetch audit logs
    let auditLogsHtml = '<span class="text-muted">Sin logs de trazabilidad</span>';
    try {
      const logsRes = await fetch(`${API}/api/patients/${encodeURIComponent(curp)}/audit-logs`);
      if (logsRes.ok) {
        const logs = await logsRes.json();
        if (logs.length > 0) {
          auditLogsHtml = logs.map(log => {
            const dateStr = _formatDateTime(log.timestamp);
            let actionBadge = '';
            if (log.action === 'REGISTRO') {
              actionBadge = `<span style="background:rgba(34,197,94,0.15);color:#22c55e;padding:1px 4px;border-radius:3px;font-weight:bold;margin-right:4px;">REGISTRO</span>`;
            } else if (log.action === 'ACTUALIZACION') {
              actionBadge = `<span style="background:rgba(6,182,212,0.15);color:#06b6d4;padding:1px 4px;border-radius:3px;font-weight:bold;margin-right:4px;">EDICIÓN</span>`;
            } else {
              actionBadge = `<span style="background:rgba(239,68,68,0.15);color:#ef4444;padding:1px 4px;border-radius:3px;font-weight:bold;margin-right:4px;">ELIMINACIÓN</span>`;
            }
            
            // Format details nicely
            let detailsStr = '';
            if (log.action === 'REGISTRO') {
              detailsStr = 'Creación del expediente inicial';
            } else if (log.action === 'ACTUALIZACION' && log.details) {
              const changes = [];
              for (const [field, val] of Object.entries(log.details)) {
                const fieldMap = {
                  primer_apellido: 'primer apellido', segundo_apellido: 'segundo apellido',
                  nombres: 'nombres', fecha_nacimiento: 'fecha de nacimiento',
                  sexo: 'sexo', folio_hospital: 'folio del hospital',
                  ubicacion_casa: 'dirección', rfc: 'RFC', nss: 'NSS',
                  expediente_externo: 'expediente externo', nacionalidad: 'nacionalidad',
                  lugar_nacimiento: 'lugar de nacimiento', estado_civil: 'estado civil',
                  ocupacion: 'ocupación', tipo_paciente: 'tipo de paciente',
                  programa_medico: 'programa médico', telefono_local: 'teléfono local',
                  celular: 'celular', email: 'correo',
                  contacto_emergencia_nombre: 'contacto de emergencia',
                  contacto_emergencia_tel: 'teléfono de emergencia',
                  anotaciones_generales: 'anotaciones', altura_cm: 'altura',
                  peso_kg: 'peso', clues_institucion: 'CLUES', aseguradoras: 'aseguradoras'
                };
                const fieldName = fieldMap[field] || field;
                let oldVal = val.old === null || val.old === undefined || val.old === '' ? '—' : val.old;
                let newVal = val.new === null || val.new === undefined || val.new === '' ? '—' : val.new;
                if (Array.isArray(oldVal)) oldVal = oldVal.join(', ');
                if (Array.isArray(newVal)) newVal = newVal.join(', ');
                changes.push(`Se actualizó <strong>${fieldName}</strong>: ${oldVal} &rarr; ${newVal}`);
              }
              detailsStr = changes.join('<br>');
            } else if (log.action === 'ELIMINACION') {
              detailsStr = 'Expediente eliminado del sistema';
            }
            
            return `
              <div style="background:rgba(255,255,255,0.03);border:1px solid var(--border);border-radius:4px;padding:8px;line-height:1.4;margin-bottom:4px;">
                <div style="display:flex;justify-content:space-between;margin-bottom:4px;opacity:0.8;">
                  <span>${actionBadge} por <strong>${_esc(log.operator)}</strong></span>
                  <span style="font-size:9px;color:#888;">${dateStr}</span>
                </div>
                <div style="color:var(--text-secondary);font-size:10px;">${detailsStr}</div>
              </div>
            `;
          }).join('');
        }
      }
    } catch (e) {
      console.error("[AuditLog] Error fetching logs:", e);
    }

    const alergias = (p.alergias || []).map(a =>
      `<span class="profile-tag tag-alergia">${_esc(a.descripcion)}${a.severidad ? ` (${a.severidad})` : ''}</span>`
    ).join('') || '<span class="text-muted">Sin alergias registradas</span>';

    const antecedentes = (p.antecedentes || []).map(a =>
      `<div class="antecedente-item"><span class="tipo-badge">${_esc(a.tipo || 'General')}</span> ${_esc(a.descripcion)}</div>`
    ).join('') || '<span class="text-muted">Sin antecedentes registrados</span>';

    return `
      <div class="overlay-nav-bar">
        <div class="overlay-nav-title">Perfil del Paciente</div>
        <button class="overlay-close-btn" onclick="OverlaySystem.close()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>

      <div class="patient-profile-layout">

        <!-- COLUMNA IZQUIERDA: Avatar + Métricas + Acciones -->
        <div class="profile-sidebar">
          <div class="profile-avatar-area">
            <div class="profile-avatar-circle">
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
            </div>
            <div class="profile-nombre">${_esc(p.nombre_completo || p.nombre || 'Paciente')}</div>
            <div class="profile-curp-badge">${_esc(p.curp)}</div>
            ${p.folio_hospital ? `<span class="folio-badge">Folio: ${_esc(p.folio_hospital)}</span>` : ''}
            <div class="problema-reciente-badge">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              Problema más reciente: <strong>${_esc(problemaReciente)}</strong>
            </div>
          </div>

          <div class="profile-metrics-card">
            <div class="metric-row"><span class="metric-label">Altura</span><span class="metric-val">${p.altura_cm ? p.altura_cm + ' cm' : '—'}</span></div>
            <div class="metric-row"><span class="metric-label">Peso</span><span class="metric-val">${p.peso_kg ? p.peso_kg + ' kg' : '—'}</span></div>
            <div class="metric-row"><span class="metric-label">BMI</span><span class="metric-val">${bmi}</span></div>
            <div class="metric-row"><span class="metric-label">Edad</span><span class="metric-val">${edad}</span></div>
            <div class="metric-row"><span class="metric-label">Sangre</span><span class="metric-val" style="color:#dc2626;">${_esc(p.tipo_sangre || '—')}</span></div>
          </div>

          <div class="profile-nav-actions">
            <button class="profile-action-btn btn-ice-qr" onclick="openIceModal('${_escAttr(p.curp)}')">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
              Pasaporte QR (ICE)
            </button>
            <button class="profile-action-btn btn-mi-salud" onclick="openPatientPortalModal('${_escAttr(p.curp)}')">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
              Portal Mi Salud Hoy
            </button>
            <button class="profile-action-btn btn-ece-fhir" onclick="downloadPatientFhir('${_escAttr(p.curp)}')">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
              Exportar HL7 FHIR R4
            </button>
            <button class="profile-action-btn btn-ask-ia" onclick="openAskForPatient('${_escAttr(p.curp)}')">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
              Ask-Expediente (IA)
            </button>
            <button class="profile-action-btn btn-historial" onclick="OverlaySystem.push('patient-events', { curp: '${_escAttr(p.curp)}', nombre: '${_escAttr(p.nombre_completo || p.nombre || '')}' })">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
              Historial Clínico Local
            </button>
          </div>
        </div>

        <!-- COLUMNA CENTRAL: Datos personales + Contacto + Social -->
        <div class="profile-main-col">

          <div class="profile-card">
            <div class="profile-card-title">Información Personal</div>
            <div class="profile-grid-2">
              <div class="profile-field"><span class="field-label">Sexo</span><span class="field-val">${_esc(p.sexo || '—')}</span></div>
              <div class="profile-field"><span class="field-label">Fecha de nacimiento</span><span class="field-val">${_esc(p.fecha_nacimiento || '—')}</span></div>
              <div class="profile-field"><span class="field-label">CURP</span><span class="field-val mono">${_esc(p.curp)}</span></div>
              <div class="profile-field"><span class="field-label">Folio Hospital (ID Local)</span><span class="field-val">${_esc(p.folio_hospital || '—')}</span></div>
              <div class="profile-field"><span class="field-label">Dirección</span><span class="field-val">${_esc(p.ubicacion_casa || '—')}</span></div>
              <div class="profile-field"><span class="field-label">Lugar de nacimiento</span><span class="field-val">${_esc(p.lugar_nacimiento || '—')}</span></div>
              <div class="profile-field"><span class="field-label">Nacionalidad</span><span class="field-val">${_esc(p.nacionalidad || '—')}</span></div>
              <div class="profile-field"><span class="field-label">RFC</span><span class="field-val mono">${_esc(p.rfc || '—')}</span></div>
              <div class="profile-field"><span class="field-label">NSS</span><span class="field-val mono">${_esc(p.nss || '—')}</span></div>
              <div class="profile-field"><span class="field-label">Exp. Externo</span><span class="field-val">${_esc(p.expediente_externo || '—')}</span></div>
            </div>
          </div>

          <div class="profile-card card-cyan">
            <div class="profile-card-title">Medios de Contacto</div>
            <div class="profile-grid-2">
              <div class="profile-field"><span class="field-label">Teléfono local</span><span class="field-val">${_esc(p.telefono_local || '—')}</span></div>
              <div class="profile-field"><span class="field-label">Celular</span><span class="field-val">${_esc(p.celular || '—')}</span></div>
              <div class="profile-field"><span class="field-label">Correo</span><span class="field-val">${_esc(p.email || '—')}</span></div>
              <div class="profile-field"><span class="field-label">Nombre familiar (emergencia)</span><span class="field-val">${_esc(p.contacto_emergencia_nombre || '—')}</span></div>
              <div class="profile-field"><span class="field-label">Tel. familiar</span><span class="field-val">${_esc(p.contacto_emergencia_tel || '—')}</span></div>
            </div>
          </div>

          <div class="profile-card card-magenta">
            <div class="profile-card-title">Perfil Social</div>
            <div class="profile-grid-2">
              <div class="profile-field"><span class="field-label">Estado civil</span><span class="field-val">${_esc(p.estado_civil || '—')}</span></div>
              <div class="profile-field"><span class="field-label">Ocupación</span><span class="field-val">${_esc(p.ocupacion || '—')}</span></div>
              <div class="profile-field"><span class="field-label">Tipo de paciente</span><span class="field-val">${_esc(p.tipo_paciente || '—')}</span></div>
              <div class="profile-field"><span class="field-label">Programa médico</span><span class="field-val">${_esc(p.programa_medico || '—')}</span></div>
              <div class="profile-field"><span class="field-label">Aseguradoras</span><span class="field-val">${Array.isArray(p.aseguradoras) && p.aseguradoras.length ? p.aseguradoras.map(_esc).join(', ') : '—'}</span></div>
            </div>
          </div>
        </div>

        <!-- COLUMNA DERECHA: Alergias, Antecedentes, Anotaciones -->
        <div class="profile-right-col">

          <div class="profile-card card-alert">
            <div class="profile-card-title">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
              Alergias
            </div>
            <div class="alergias-list">${alergias}</div>
          </div>

          <div class="profile-card">
            <div class="profile-card-title">Antecedentes y su tipo</div>
            <div class="antecedentes-list">${antecedentes}</div>
          </div>

          <div class="profile-card">
            <div class="profile-card-title">Anotaciones del Paciente</div>
            <div class="anotaciones-text">${_esc(p.anotaciones_generales || '—')}</div>
          </div>

          <div class="profile-card" style="border-left: 2.5px solid var(--accent-magenta);">
            <div class="profile-card-title" style="display:flex;align-items:center;gap:6px;">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
              Logs de Trazabilidad / Auditoría
            </div>
            <div class="audit-logs-list" style="max-height: 250px; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; margin-top: 10px;">
              ${auditLogsHtml}
            </div>
          </div>
        </div>

      </div>

      <div class="overlay-footer">
        <span class="overlay-footer-lock">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
          Datos protegidos — Confidencial
        </span>
        <div class="overlay-footer-actions">
          <button class="overlay-btn-danger" style="background:#dc2626 !important;color:#fff !important;border:none !important;" onclick="_deletePatient('${_escAttr(p.curp)}', '${_escAttr(p.nombre_completo || p.nombre || '')}')">🗑️ Eliminar Expediente</button>
          <button class="overlay-btn-cancel" onclick="OverlaySystem.push('edit-patient-profile', { curp: '${_escAttr(p.curp)}' })">✏️ Editar datos</button>
          <button class="overlay-btn-danger" onclick="OverlaySystem.close()">🚪 Salir</button>
        </div>
      </div>
    `;
  }

  // ── RENDER: EDITAR PERFIL DEL PACIENTE ───────────────────────────────────
  // (mismo formulario que registro, pre-rellenado con datos actuales)

  async function renderEditPatientProfile(data) {
    const curp = data.curp;
    const res = await fetch(`${API}/api/patients/${encodeURIComponent(curp)}`);
    if (!res.ok) throw new Error('No se pudo cargar el perfil para edición');
    const p = await res.json();

    const v = (field) => {
      const val = p[field];
      if (Array.isArray(val)) {
        return _esc(val.join(', '));
      }
      return _esc(val || '');
    };

    return `
      <div class="overlay-nav-bar">
        <button class="overlay-back-btn" onclick="OverlaySystem.pop()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
          Volver al perfil
        </button>
        <div class="overlay-nav-title">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          Editar datos del paciente
        </div>
        <button class="overlay-close-btn" onclick="OverlaySystem.close()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>

      <!-- Aviso NOM-004 -->
      <div style="display:flex;align-items:center;gap:8px;padding:10px 24px;background:rgba(245,158,11,0.06);border-bottom:1px solid rgba(245,158,11,0.2);font-size:11px;color:#fcd34d;flex-shrink:0;">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
        Solo se editan datos demográficos y de contacto. Las notas médicas y recetas son inmutables (NOM-004-SSA3-2012).
      </div>

      <form id="edit-patient-form" style="flex:1;overflow-y:auto;" onsubmit="event.preventDefault(); _submitEditPatient('${_escAttr(curp)}')">
        <div class="register-form-scroll" style="max-height:none;padding:20px 24px;">

          <!-- IDENTIFICACIÓN -->
          <div class="register-section-title">Identificación</div>
          <div class="register-grid">
            <div class="form-group"><label>Primer Apellido</label><input class="input-field" name="primer_apellido" value="${v('primer_apellido')}" /></div>
            <div class="form-group"><label>Segundo Apellido</label><input class="input-field" name="segundo_apellido" value="${v('segundo_apellido')}" /></div>
            <div class="form-group"><label>Nombre(s)</label><input class="input-field" name="nombres" value="${v('nombres')}" /></div>
            <div class="form-group"><label>Fecha de Nacimiento</label><input class="input-field" type="date" name="fecha_nacimiento" value="${v('fecha_nacimiento')}" /></div>
            <div class="form-group"><label>Sexo</label>
              <select class="input-field" name="sexo">
                <option value="">— Seleccionar —</option>
                <option value="Masculino" ${p.sexo === 'Masculino' ? 'selected' : ''}>Masculino</option>
                <option value="Femenino" ${p.sexo === 'Femenino' ? 'selected' : ''}>Femenino</option>
              </select>
            </div>
            <div class="form-group"><label>Tipo de Sangre</label>
              <select class="input-field" name="tipo_sangre">
                <option value="">— Seleccionar —</option>
                ${['O+','O-','A+','A-','B+','B-','AB+','AB-'].map(bt =>
                  `<option value="${bt}" ${p.tipo_sangre === bt ? 'selected' : ''}>${bt}</option>`).join('')}
              </select>
            </div>
            <div class="form-group"><label>CURP</label><input class="input-field" name="curp_field" value="${v('curp')}" style="font-family:'JetBrains Mono',monospace;" /></div>
          </div>

          <!-- DOCUMENTOS -->
          <div class="register-section-title">Documentos e Identificadores</div>
          <div class="register-grid">
            <div class="form-group"><label>No. Expediente Hospital (Folio)</label><input class="input-field" name="folio_hospital" value="${v('folio_hospital')}" /></div>
            <div class="form-group"><label>RFC</label><input class="input-field" name="rfc" value="${v('rfc')}" style="font-family:'JetBrains Mono',monospace;" /></div>
            <div class="form-group"><label>NSS (Seguro Social)</label><input class="input-field" name="nss" value="${v('nss')}" /></div>
            <div class="form-group"><label>No. Expediente Externo</label><input class="input-field" name="expediente_externo" value="${v('expediente_externo')}" /></div>
            <div class="form-group"><label>Nacionalidad</label><input class="input-field" name="nacionalidad" value="${v('nacionalidad')}" /></div>
            <div class="form-group"><label>Lugar de Nacimiento</label><input class="input-field" name="lugar_nacimiento" value="${v('lugar_nacimiento')}" /></div>
          </div>

          <!-- DOMICILIO -->
          <div class="register-section-title">Domicilio</div>
          <div class="form-group" style="grid-column:1/-1;"><label>Dirección / Ubicación de casa</label>
            <input class="input-field" name="ubicacion_casa" value="${v('ubicacion_casa')}" />
          </div>

          <!-- PERFIL SOCIAL -->
          <div class="register-section-title">Perfil Social</div>
          <div class="register-grid">
            <div class="form-group"><label>Estado Civil</label>
              <select class="input-field" name="estado_civil">
                <option value="">— Seleccionar —</option>
                ${['Soltero/a','Casado/a','Divorciado/a','Viudo/a','Unión libre'].map(o =>
                  `<option value="${o}" ${p.estado_civil === o ? 'selected' : ''}>${o}</option>`).join('')}
              </select>
            </div>
            <div class="form-group"><label>Ocupación</label><input class="input-field" name="ocupacion" value="${v('ocupacion')}" /></div>
            <div class="form-group"><label>Tipo de Paciente</label>
              <select class="input-field" name="tipo_paciente">
                <option value="">— Seleccionar —</option>
                ${['Urgencias','Consulta externa','Hospitalización','Referido'].map(o =>
                  `<option value="${o}" ${p.tipo_paciente === o ? 'selected' : ''}>${o}</option>`).join('')}
              </select>
            </div>
            <div class="form-group"><label>Programa Médico/Social</label><input class="input-field" name="programa_medico" value="${v('programa_medico')}" /></div>
          </div>

          <!-- MÉTRICAS FÍSICAS -->
          <div class="register-section-title">Métricas Físicas</div>
          <div class="register-grid">
            <div class="form-group"><label>Altura (cm)</label><input class="input-field" type="number" name="altura_cm" value="${p.altura_cm || ''}" placeholder="Ej: 168" /></div>
            <div class="form-group"><label>Peso (kg)</label><input class="input-field" type="number" step="0.1" name="peso_kg" value="${p.peso_kg || ''}" placeholder="Ej: 72.5" /></div>
          </div>

          <!-- CONTACTO -->
          <div class="register-section-title">Medios de Contacto</div>
          <div class="register-grid">
            <div class="form-group"><label>Teléfono local</label><input class="input-field" type="tel" name="telefono_local" value="${v('telefono_local')}" /></div>
            <div class="form-group"><label>Celular (con prefijo, ej. +52)</label><input class="input-field" type="tel" name="celular" value="${v('celular')}" /></div>
            <div class="form-group"><label>Correo electrónico</label><input class="input-field" type="email" name="email" value="${v('email')}" /></div>
          </div>

          <!-- EMERGENCIA -->
          <div class="register-section-title">Contacto de Emergencia</div>
          <div class="register-grid">
            <div class="form-group"><label>Nombre del familiar</label><input class="input-field" name="contacto_emergencia_nombre" value="${v('contacto_emergencia_nombre')}" /></div>
            <div class="form-group"><label>Teléfono del familiar</label><input class="input-field" type="tel" name="contacto_emergencia_tel" value="${v('contacto_emergencia_tel')}" /></div>
          </div>

          <!-- SEGUROS Y NOTAS -->
          <div class="register-section-title">Seguros y Anotaciones</div>
          <div class="form-group"><label>Aseguradoras</label><input class="input-field" name="aseguradoras" value="${v('aseguradoras')}" placeholder="Ej: IMSS, Seguros Atlas" /></div>
          <div class="form-group"><label>Anotaciones generales</label>
            <textarea class="textarea-field" name="anotaciones_generales" rows="3">${_esc(p.anotaciones_generales || '')}</textarea>
          </div>

        </div><!-- /register-form-scroll -->

        <!-- FOOTER STICKY -->
        <div class="overlay-footer">
          <span class="overlay-footer-lock">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
            Solo datos demográficos — Notas inmutables
          </span>
          <div class="overlay-footer-actions">
            <button type="button" class="overlay-btn-cancel" onclick="OverlaySystem.pop()">Cancelar</button>
            <button type="submit" class="overlay-btn-confirm" id="edit-save-btn">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
              Guardar cambios
            </button>
          </div>
        </div>
      </form>
    `;
  }

  // ── RENDER: HISTORIAL — EVENTOS CLÍNICOS ──────────────────────────────────

  async function renderPatientEvents(data) {
    const { curp, nombre } = data;
    const res = await fetch(`${API}/api/patients/${encodeURIComponent(curp)}/events`);
    if (!res.ok) throw new Error('No se pudieron cargar los eventos');
    const eventos = await res.json();

    const eventColors = ['var(--accent-cyan)', 'var(--accent-magenta)', '#22c55e', '#f59e0b', '#8b5cf6'];

    const eventosList = eventos.length === 0
      ? '<div class="overlay-empty-state">Sin eventos clínicos registrados.<br><small>Crea uno desde "Nueva Consulta".</small></div>'
      : eventos.map((e, idx) => {
          const color = eventColors[idx % eventColors.length];
          const fechaCreacion = _formatDate(e.fecha_hora_creacion || e.created_at);
          const ultimaMod = _formatDateTime(e.ultima_consulta || e.updated_at);
          const eventIconPaths = [
            'M12 1v22M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6', // medical
            'M22 12h-4l-3 9L9 3l-3 9H2', // heartbeat
            'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z', // shield
            'M9 12h6m-6 4h6m2 5H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5.586a1 1 0 0 1 .707.293l5.414 5.414a1 1 0 0 1 .293.707V19a2 2 0 0 1-2 2z', // file
          ];
          const iconPath = eventIconPaths[idx % eventIconPaths.length];
          return `
            <div class="timeline-item-v2" data-event-id="${_escAttr(e.id)}" onclick="OverlaySystem.push('event-consultas', { evento_id: '${_escAttr(e.id)}', evento_nombre: '${_escAttr(e.nombre_evento)}', curp: '${_escAttr(curp)}', nombre: '${_escAttr(nombre)}' })">
              <!-- Date column left -->
              <div class="tv2-date-col">
                <span class="tv2-day">${_getDay(e.fecha_hora_creacion || e.created_at)}</span>
                <span class="tv2-month">${_getMonthAbbr(e.fecha_hora_creacion || e.created_at)}</span>
                <span class="tv2-year">${_getYear(e.fecha_hora_creacion || e.created_at)}</span>
              </div>
              <!-- Timeline line + dot -->
              <div class="tv2-connector">
                <div class="tv2-dot" style="background:${color};box-shadow:0 0 8px ${color}40;"></div>
                <div class="tv2-line"></div>
              </div>
              <!-- Card -->
              <div class="tv2-card" style="border-left:3px solid ${color};">
                <div class="tv2-card-icon" style="background:${color}20;border:1px solid ${color}40;">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="${color}" stroke-width="1.5"><path d="${iconPath}"/></svg>
                </div>
                <div class="tv2-card-body">
                  <div class="tv2-nombre-row">
                    <span class="tv2-nombre">${_esc(e.nombre_evento)}</span>
                    <button class="tv2-edit-inline" onclick="event.stopPropagation(); _promptRenameEvento('${_escAttr(e.id)}', '${_escAttr(e.nombre_evento)}', '${_escAttr(curp)}', '${_escAttr(nombre)}')" title="Renombrar">
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                    </button>
                  </div>
                  <div class="tv2-meta-row">
                    <span class="tv2-consultas-badge" style="color:${color};background:${color}15;border:1px solid ${color}30;">
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
                      ${e.num_consultas} consulta${e.num_consultas !== 1 ? 's' : ''}
                    </span>
                    <span class="tv2-doctor">
                      <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                      Doctor: ${_esc(e.doctor_creador || '—')}
                    </span>
                  </div>
                </div>
                <div class="tv2-card-right">
                  <div class="tv2-ultima-mod">
                    <span class="tv2-mod-label">
                      <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                      Última modificación
                    </span>
                    <span class="tv2-mod-date">${ultimaMod}</span>
                  </div>
                  <button class="tv2-edit-btn" onclick="event.stopPropagation(); _promptRenameEvento('${_escAttr(e.id)}', '${_escAttr(e.nombre_evento)}', '${_escAttr(curp)}', '${_escAttr(nombre)}')">
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
                    Editar
                  </button>
                </div>
              </div>
            </div>
          `;
        }).join('');

    return `
      <div class="overlay-nav-bar">
        <button class="overlay-back-btn" onclick="OverlaySystem.pop()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
          Atrás
        </button>
        <div class="overlay-nav-title" style="font-size:18px;font-weight:700;">Eventos clínicos del paciente</div>
        <button class="overlay-close-btn" onclick="OverlaySystem.close()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>

      <div style="display:flex;align-items:center;gap:12px;padding:8px 24px 12px;border-bottom:1px solid var(--border);flex-shrink:0;">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent-cyan)" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
        <strong style="font-size:13px;color:var(--text-primary);">${_esc(nombre || curp)}</strong>
        <span class="patient-id-badge">ID: ${_esc(curp)}</span>
        <div style="flex:1;"></div>
        <div style="display:flex;align-items:center;gap:8px;background:var(--bg-input);border:1.5px solid var(--accent-cyan);border-radius:var(--radius-sm);padding:8px 14px;min-width:260px;">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
          <input type="text" placeholder="Buscar eventos clínicos..." class="overlay-search-input" oninput="_filterTimeline(this.value, '${_escAttr(curp)}')" style="background:transparent;border:none;outline:none;color:var(--text-primary);font-size:13px;width:100%;font-family:'Inter',sans-serif;" />
        </div>
      </div>

      <div class="timeline-container" id="timeline-container" style="flex:1;overflow-y:auto;padding:24px;">
        ${eventosList}
      </div>
    `;
  }

  // ── RENDER: CONSULTAS DE UN EVENTO ────────────────────────────────────────

  async function renderEventConsultas(data) {
    const { evento_id, evento_nombre, curp, nombre } = data;
    const res = await fetch(`${API}/api/consultations/event/${encodeURIComponent(evento_id)}`);
    if (!res.ok) throw new Error('No se pudieron cargar las consultas');
    const consultas = await res.json();

    const nodeColors = ['#22c55e', '#06b6d4', '#8b5cf6', '#f59e0b', '#ec4899', '#6b7280', '#ef4444'];

    const timelineNodes = consultas.map((c, idx) => {
      const color = nodeColors[idx % nodeColors.length];
      const fecha = _formatDate(c.fecha_hora);
      return `
        <div class="h-timeline-node ${idx === 0 ? 'active' : ''}"
             onclick="_selectConsultaNode(${idx}, '${_escAttr(evento_id)}')"
             id="h-node-${idx}">
          <div class="h-node-circle" style="background: ${color};">${idx + 1}</div>
          <div class="h-node-label">Consulta ${idx + 1}</div>
          <div class="h-node-date">${fecha}</div>
        </div>
        ${idx < consultas.length - 1 ? '<div class="h-timeline-connector"></div>' : ''}
      `;
    }).join('');

    // Serialize consultas as JSON for the selection function
    const consultasJson = JSON.stringify(consultas).replace(/'/g, "\\'").replace(/"/g, '&quot;');

    const firstConsulta = consultas[0];

    // Obtener metadatos del evento (primer registro + última modificación)
    let eventoMeta = { fecha_hora_creacion: null, ultima_consulta: null, updated_at: null };
    try {
      const evRes = await fetch(`${API}/api/patients/${encodeURIComponent(curp)}/events`);
      if (evRes.ok) {
        const evList = await evRes.json();
        const ev = evList.find(e => e.id === evento_id);
        if (ev) eventoMeta = ev;
      }
    } catch { /* silent */ }

    const fechaPrimerRegistro = _formatDateTime(eventoMeta.fecha_hora_creacion || eventoMeta.created_at);
    const fechaUltimaMod = _formatDateTime(eventoMeta.ultima_consulta || eventoMeta.updated_at);

    return `
      <div class="overlay-nav-bar">
        <button class="overlay-back-btn" onclick="OverlaySystem.pop()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
          Atrás
        </button>
        <div class="overlay-nav-title">
          ${_esc(evento_nombre)}
          <button class="edit-evento-inline" onclick="_promptRenameEvento('${_escAttr(evento_id)}', '${_escAttr(evento_nombre)}', '${_escAttr(curp)}', '${_escAttr(nombre)}')" title="Renombrar">
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 1 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/></svg>
          </button>
        </div>
        <button class="overlay-close-btn" onclick="OverlaySystem.close()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
        </button>
      </div>

      <!-- Metadatos del evento: paciente + primer registro + última modificación -->
      <div class="overlay-patient-header">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
        Paciente: <strong>${_esc(nombre || curp)}</strong>
        <span class="patient-id-badge">ID: ${_esc(curp)}</span>
        <span class="evento-meta-sep">•</span>
        <span class="evento-meta-item">📅 Primer registro: ${fechaPrimerRegistro}</span>
        <span class="evento-meta-sep">•</span>
        <span class="evento-meta-item">⏰ Última modificación: ${fechaUltimaMod}</span>
      </div>

      ${consultas.length === 0 ? '<div class="overlay-empty-state">Sin consultas registradas para este evento.</div>' : `
        <!-- LÍNEA DE TIEMPO HORIZONTAL -->
        <div class="h-timeline-wrapper">
          <button class="h-timeline-arrow left" onclick="_scrollTimeline(-200)" id="h-arrow-left">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
          </button>
          <div class="h-timeline-scroll" id="h-timeline-scroll">
            <div class="h-timeline-track">
              ${timelineNodes}
            </div>
          </div>
          <button class="h-timeline-arrow right" onclick="_scrollTimeline(200)" id="h-arrow-right">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
          </button>
        </div>

        <!-- DETALLE DE CONSULTA SELECCIONADA -->
        <div class="consulta-detail-area" id="consulta-detail-area" data-consultas="${consultasJson}">
          ${firstConsulta ? _renderConsultaDetail(firstConsulta, 0) : ''}
        </div>
      `}
    `;
  }

  // ── RENDER: DETALLE DE UNA CONSULTA ──────────────────────────────────────

  function _renderConsultaDetail(c, idx) {
    const nota = c.nota_medica || {};
    const receta = c.receta || {};
    const meds = receta.medicamentos || [];

    return `
      <div class="consulta-detail-header">
        <div class="consulta-detail-meta">
          <span>📅 ${_formatDateTime(c.fecha_hora)}</span>
          <span>👤 Doctor: ${_esc(c.doctor_nombre || '—')}</span>
        </div>
        <button class="btn-ver-detalle" onclick="window.showToast?.('Vista completa próximamente', 'info')">
          Ver detalle completo ↗
        </button>
      </div>

      <div class="consulta-cards-row">
        <!-- Notas del doctor -->
        <div class="consulta-doc-card">
          <div class="doc-card-title">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 0 2 2z"/></svg>
            Notas del doctor
          </div>
          <div class="doc-card-body">
            ${c.resumen_doctor
              ? `<p>${_esc(c.resumen_doctor)}</p>`
              : '<span class="text-muted">Sin notas adicionales del doctor</span>'}
          </div>
        </div>

        <!-- Nota médica -->
        <div class="consulta-doc-card">
          <div class="doc-card-title">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            Acceso a la Nota médica
          </div>
          <div class="doc-card-body">
            <p class="text-muted-sm">Consulta completa con evaluación, exploración física y plan de manejo.</p>
            <p><strong>Motivo:</strong> ${_esc(nota.motivo_consulta || '—')}</p>
            <p><strong>Diagnóstico:</strong> ${_esc(nota.diagnostico_integral || '—')}</p>
          </div>
          <button class="doc-card-btn" onclick="_openNotaMedicaConsulta('${_escAttr ? _escAttr(c.id || '') : (c.id || '')}')">
            Ver nota médica ↗
          </button>
        </div>

        <!-- Receta médica -->
        <div class="consulta-doc-card">
          <div class="doc-card-title">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/></svg>
            Acceso a la receta médica
          </div>
          <div class="doc-card-body">
            <p class="text-muted-sm">Medicamentos prescritos, dosis, duración y recomendaciones.</p>
            <p><strong>${meds.length} medicamento${meds.length !== 1 ? 's' : ''} prescrito${meds.length !== 1 ? 's' : ''}</strong></p>
          </div>
          <button class="doc-card-btn" onclick="_openRecetaConsulta('${_escAttr ? _escAttr(c.id || '') : (c.id || '')}')">
            Ver receta médica ↗
          </button>
        </div>
      </div>

      ${c.notas_addendum ? `
        <div class="addendum-block">
          <strong>Addendum:</strong>
          <pre>${_esc(c.notas_addendum)}</pre>
        </div>
      ` : ''}
    `;
  }

  // ── HELPERS INTERNOS ──────────────────────────────────────────────────────

  function _esc(str) {
    if (!str && str !== 0) return '';
    const d = document.createElement('div');
    d.textContent = String(str);
    return d.innerHTML;
  }

  function _escAttr(str) {
    if (!str) return '';
    return String(str).replace(/'/g, "\\'").replace(/"/g, '\\"');
  }

  function _formatDate(iso) {
    if (!iso) return '—';
    try {
      return new Date(iso).toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' });
    } catch { return iso; }
  }

  function _formatDateTime(iso) {
    if (!iso) return '—';
    try {
      const d = new Date(iso);
      return d.toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' }) + ' ' +
             d.toLocaleTimeString('es-MX', { hour: '2-digit', minute: '2-digit' });
    } catch { return iso; }
  }

  function _getDay(iso) {
    if (!iso) return '—';
    try { return new Date(iso).getDate().toString().padStart(2, '0'); } catch { return '—'; }
  }

  function _getMonthAbbr(iso) {
    if (!iso) return '—';
    try { return new Date(iso).toLocaleDateString('es-MX', { month: 'short' }).toUpperCase(); } catch { return '—'; }
  }

  function _getYear(iso) {
    if (!iso) return '—';
    try { return new Date(iso).getFullYear(); } catch { return '—'; }
  }

  // Exposición pública
  return { open, push, pop, close, _renderConsultaDetail };
})();

// ── FUNCIONES GLOBALES (llamadas desde HTML generado dinámicamente) ──────────

window.OverlaySystem = OverlaySystem;

window._selectConsultaNode = function(idx, eventoId) {
  const detailArea = document.getElementById('consulta-detail-area');
  if (!detailArea) return;
  const consultas = JSON.parse(detailArea.dataset.consultas || '[]');
  if (!consultas[idx]) return;

  // Update active node visual
  document.querySelectorAll('.h-timeline-node').forEach((n, i) => {
    n.classList.toggle('active', i === idx);
  });

  detailArea.innerHTML = OverlaySystem._renderConsultaDetail(consultas[idx], idx);
};

window._scrollTimeline = function(delta) {
  const scrollEl = document.getElementById('h-timeline-scroll');
  if (scrollEl) scrollEl.scrollBy({ left: delta, behavior: 'smooth' });
};

// ── GUARDAR EDICIÓN DEL PERFIL ────────────────────────────────────────────────
window._submitEditPatient = async function(curp) {
  const form = document.getElementById('edit-patient-form');
  if (!form) return;

  const saveBtn = document.getElementById('edit-save-btn');
  if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = 'Guardando...'; }

  // Recopilar todos los campos del formulario
  const fd = new FormData(form);
  const payload = {};
  fd.forEach((val, key) => {
    if (val !== '') payload[key] = val;
  });

  // Aseguradoras serialization (should be a JSON array of strings)
  const asegInput = form.querySelector('[name="aseguradoras"]');
  if (asegInput) {
    payload.aseguradoras = asegInput.value
      .split(',')
      .map(s => s.trim())
      .filter(Boolean);
  }

  // Normalizar nombre: curp_field es solo referencia, no lo enviamos como key 'curp_field'
  if (payload.curp_field) {
    payload.curp = payload.curp_field;
    delete payload.curp_field;
  }

  // Convertir números
  if (payload.altura_cm) payload.altura_cm = parseFloat(payload.altura_cm);
  if (payload.peso_kg)   payload.peso_kg   = parseFloat(payload.peso_kg);

  try {
    const res = await fetch(`/api/patients/${encodeURIComponent(curp)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const err = await res.text();
      throw new Error(err);
    }
    window.showToast?.('Datos del paciente actualizados correctamente', 'success');

    // Refrescar lista de pacientes en el panel izquierdo
    window.loadPatients?.();

    // Regresar al perfil actualizado
    OverlaySystem.open('patient-profile', { curp });

  } catch (err) {
    window.showToast?.('Error al guardar: ' + err.message, 'error');
    if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = 'Guardar cambios'; }
  }
};


window._deletePatient = async function(curp, nombre) {
  if (!curp) return;
  
  // Primera confirmación
  const firstConfirm = confirm(`¿Está seguro de que desea eliminar el expediente de ${nombre} (CURP: ${curp})?\n\nEsta acción eliminará de forma permanente el perfil y todo su historial de consultas.`);
  if (!firstConfirm) return;
  
  // Segunda confirmación
  const secondConfirm = confirm(`ADVERTENCIA: Esta acción es irreversible.\n¿Realmente desea eliminar todos los datos clínicos de ${nombre}?`);
  if (!secondConfirm) return;
  
  try {
    const res = await fetch(`/api/patients/${encodeURIComponent(curp)}`, {
      method: 'DELETE',
    });
    if (!res.ok) {
      const err = await res.text();
      throw new Error(err);
    }
    window.showToast?.('Expediente eliminado correctamente', 'success');
    
    // Cerrar overlay y recargar lista de pacientes
    OverlaySystem.close();
    window.loadPatients?.();
  } catch (err) {
    window.showToast?.('Error al eliminar: ' + err.message, 'error');
    console.error(err);
  }
};



window._promptRenameEvento = async function(eventoId, currentName, curp, nombre) {
  const newName = prompt('Nuevo nombre para el evento clínico:', currentName);
  if (!newName || !newName.trim()) return;
  try {
    const res = await fetch(`/api/patients/${encodeURIComponent(curp)}/events/${encodeURIComponent(eventoId)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ nombre_evento: newName.trim() }),
    });
    if (!res.ok) throw new Error(await res.text());
    window.showToast?.('Evento renombrado correctamente', 'success');
    // Reload the events view
    OverlaySystem.open('patient-events', { curp, nombre });
  } catch (err) {
    window.showToast?.('Error al renombrar el evento', 'error');
    console.error(err);
  }
};

window._filterTimeline = async function(query, curp) {
  const items = document.querySelectorAll('.timeline-item, .timeline-item-v2');
  if (!query || !query.trim()) {
    items.forEach(item => item.style.display = '');
    return;
  }
  
  const q = query.toLowerCase();
  
  // 1. Intenta búsqueda semántica en el backend si curp está disponible
  if (curp) {
    try {
      const res = await fetch(`/api/patients/${encodeURIComponent(curp)}/events/search?q=${encodeURIComponent(query)}`);
      if (res.ok) {
        const results = await res.json();
        // results es un array de { event_id: "...", similitud: 0.8... }
        const matchingIds = new Set(results.map(r => r.event_id));
        
        items.forEach(item => {
          const eventId = item.getAttribute('data-event-id');
          // Si coincide semánticamente o por texto local (fallback)
          const text = item.textContent.toLowerCase();
          const matchesText = text.includes(q);
          const matchesSemantic = eventId && matchingIds.has(eventId);
          
          item.style.display = (matchesText || matchesSemantic) ? '' : 'none';
        });
        return;
      }
    } catch (err) {
      console.warn("[SemanticSearch] Error querying backend:", err);
    }
  }
  
  // Fallback: búsqueda por texto local tradicional
  items.forEach(item => {
    const text = item.textContent.toLowerCase();
    item.style.display = text.includes(q) ? '' : 'none';
  });
};

// Cerrar overlay al hacer click en el fondo
document.addEventListener('click', (e) => {
  if (e.target.id === 'app-overlay') OverlaySystem.close();
});

// Cerrar con Escape
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    const overlay = document.getElementById('app-overlay');
    if (overlay?.classList.contains('open')) OverlaySystem.close();
  }
});

// ── VISOR: Nota Médica NOM-004 (por consulta_id) ─────────────────────────────
window._openNotaMedicaConsulta = async function(consultaId) {
  if (!consultaId) return window.showToast?.('Sin ID de consulta', 'error');
  try {
    const res = await fetch(`/api/consultations/${encodeURIComponent(consultaId)}/nota`);
    if (!res.ok) throw new Error('No se pudo cargar la nota médica');
    const data = await res.json();
    const htmlContent = data.nota_medica_html || data.nota_clinica
      ? `<pre style="font-family:Inter,sans-serif;white-space:pre-wrap;padding:20px;">${JSON.stringify(data.nota_clinica || data, null, 2)}</pre>`
      : '<p style="padding:20px;color:#666;">Nota médica no disponible</p>';
    const pw = window.open('', '_blank', 'width=860,height=750');
    if (pw) {
      pw.document.write(`
        <!DOCTYPE html><html lang="es"><head>
          <meta charset="UTF-8"><title>Nota Médica — MedicAItion</title>
          <link rel="preconnect" href="https://fonts.googleapis.com">
          <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
          <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { font-family: 'Inter', sans-serif; background: #fff; color: #1a1a1a; padding: 32px; }
            h1 { font-size: 20px; color: #dc2626; border-bottom: 2px solid #dc2626; padding-bottom: 8px; margin-bottom: 20px; }
            .nom-section { margin-bottom: 16px; }
            .nom-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.7px; color: #666; margin-bottom: 4px; }
            .nom-val { font-size: 13px; line-height: 1.7; }
            @media print { body { padding: 0; } }
          </style>
        </head><body>
          <h1>Nota de Evolución — NOM-004-SSA3-2012</h1>
          ${htmlContent}
          <p style="margin-top:24px;font-size:11px;color:#999;">Generado por MedicAItion • Inmutable según NOM-004</p>
        </body></html>`);
      pw.document.close();
    }
  } catch (err) {
    window.showToast?.('Error al abrir la nota médica: ' + err.message, 'error');
  }
};

// ── VISOR: Receta Médica (por consulta_id) ────────────────────────────────────
window._openRecetaConsulta = async function(consultaId) {
  if (!consultaId) return window.showToast?.('Sin ID de consulta', 'error');
  try {
    const res = await fetch(`/api/consultations/${encodeURIComponent(consultaId)}/receta`);
    if (!res.ok) throw new Error('No se pudo cargar la receta');
    const data = await res.json();
    const receta = data.receta || data;
    const meds = receta.medicamentos || [];
    const medsRows = meds.map(m => `
      <tr>
        <td>${m.nombre || '—'}</td>
        <td>${m.dosis || '—'}</td>
        <td>${m.via || '—'}</td>
        <td>${m.periodicidad || '—'}</td>
        <td>${m.duracion || '—'}</td>
      </tr>`).join('') || '<tr><td colspan="5" style="text-align:center;color:#999;">Sin medicamentos registrados</td></tr>';
    const pw = window.open('', '_blank', 'width=860,height=750');
    if (pw) {
      pw.document.write(`
        <!DOCTYPE html><html lang="es"><head>
          <meta charset="UTF-8"><title>Receta Médica — MedicAItion</title>
          <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap" rel="stylesheet">
          <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { font-family: 'Inter', sans-serif; background: #fff; color: #1a1a1a; padding: 32px; }
            h1 { font-size: 20px; color: #dc2626; border-bottom: 2px solid #dc2626; padding-bottom: 8px; margin-bottom: 20px; }
            table { width: 100%; border-collapse: collapse; font-size: 13px; margin-top: 16px; }
            th { text-align: left; background: #f9fafb; padding: 8px 12px; font-weight: 600; border-bottom: 2px solid #e5e7eb; }
            td { padding: 8px 12px; border-bottom: 1px solid #f3f4f6; }
            .instrucciones { margin-top: 20px; padding: 12px; background: #f9fafb; border-radius: 6px; font-size: 13px; }
            @media print { body { padding: 0; } }
          </style>
        </head><body>
          <h1>Receta Médica</h1>
          <p style="font-size:13px;color:#666;margin-bottom:16px;">
            Paciente: ${receta.paciente_nombre || '—'} &nbsp;|&nbsp;
            Fecha: ${receta.fecha || data.fecha_hora || '—'} &nbsp;|&nbsp;
            Doctor: ${receta.doctor || data.doctor_nombre || '—'}
          </p>
          <table>
            <thead><tr><th>Medicamento</th><th>Dosis</th><th>Vía</th><th>Periodicidad</th><th>Duración</th></tr></thead>
            <tbody>${medsRows}</tbody>
          </table>
          ${receta.instrucciones_generales ? `<div class="instrucciones"><strong>Indicaciones:</strong><br>${receta.instrucciones_generales}</div>` : ''}
          <p style="margin-top:24px;font-size:11px;color:#999;">Generado por MedicAItion • Documento oficial</p>
        </body></html>`);
      pw.document.close();
    }
  } catch (err) {
    window.showToast?.('Error al abrir la receta: ' + err.message, 'error');
  }
};


// Soporte drag-to-scroll en la línea de tiempo horizontal
document.addEventListener('mousedown', (e) => {
  const track = e.target.closest('#h-timeline-scroll');
  if (!track) return;
  let startX = e.pageX - track.offsetLeft;
  let scrollLeft = track.scrollLeft;
  let isDragging = true;
  track.style.cursor = 'grabbing';

  const onMove = (ev) => {
    if (!isDragging) return;
    const x = ev.pageX - track.offsetLeft;
    const walk = (x - startX) * 1.5;
    track.scrollLeft = scrollLeft - walk;
  };
  const onUp = () => {
    isDragging = false;
    track.style.cursor = '';
    document.removeEventListener('mousemove', onMove);
    document.removeEventListener('mouseup', onUp);
  };
  document.addEventListener('mousemove', onMove);
  document.addEventListener('mouseup', onUp);
});
