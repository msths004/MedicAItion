/**
 * specialized_care.js — Atención Especializada y Expediente Clínico Activo
 * =========================================================================
 * Vista clínica integral de 3 columnas (Resumen IA + Vitales NEWS2 + Historial |
 * Nota SOAP con Dictado | Receta Electrónica + Seguridad Alergias + Órdenes + Firma NOM-004).
 */

const _ExpCareState = {
  curp: null,
  patient: null,
  events: [],
  allergies: [],
  vitals: null,
  meds: [],
  labs: new Set(['Biometría hemática', 'Química sanguínea', 'Examen general de orina']),
  selectedLabs: new Set(),
  editMode: false,
  timerSeconds: 0,
  timerInterval: null,
  timerPaused: false,
  isDictating: false,
  recognition: null,
  soap: {
    s: '',
    o: '',
    a: '',
    p: '[PENDIENTE: plan y tratamiento]',
  },
};

function _expEsc(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function openSpecializedCare(curp) {
  if (curp) _ExpCareState.curp = curp.toUpperCase();
  if (typeof switchMainTab === 'function') switchMainTab('expediente');
}

async function initSpecializedCareView() {
  await _populateExpPatientSelector();
  const target = _ExpCareState.curp
    || AppState.selectedPatientCurp
    || document.getElementById('exp-patient-select')?.value;

  if (target) {
    const sel = document.getElementById('exp-patient-select');
    if (sel) sel.value = target;
    await loadSpecializedPatient(target);
  }
  _startExpTimer();
}

async function _populateExpPatientSelector() {
  const sel = document.getElementById('exp-patient-select');
  if (!sel) return;
  try {
    const res = await fetch(`${API}/api/patients/`);
    if (!res.ok) return;
    const data = await res.json();
    const list = Array.isArray(data) ? data : (data.patients || []);
    const prev = _ExpCareState.curp || sel.value;
    sel.innerHTML = list.length
      ? list.map(p => {
          const name = `${p.nombres || ''} ${p.primer_apellido || ''} ${p.segundo_apellido || ''}`.trim() || p.curp;
          return `<option value="${_expEsc(p.curp)}">${_expEsc(name)} (${_expEsc(p.curp)})</option>`;
        }).join('')
      : '<option value="">Sin pacientes registrados</option>';
    if (prev && [...sel.options].some(o => o.value === prev)) {
      sel.value = prev;
    } else if (list.length) {
      _ExpCareState.curp = list[0].curp;
    }
  } catch (e) {
    console.warn('[Expediente] Error cargando lista de pacientes:', e);
  }
}

async function loadSpecializedPatient(curp) {
  if (!curp) return;
  _ExpCareState.curp = curp.toUpperCase();
  AppState.selectedPatientCurp = _ExpCareState.curp;

  try {
    const [pRes, evRes, vitRes, conRes] = await Promise.all([
      fetch(`${API}/api/patients/${encodeURIComponent(_ExpCareState.curp)}`),
      fetch(`${API}/api/patients/${encodeURIComponent(_ExpCareState.curp)}/events`),
      fetch(`${API}/api/wearables/readings?curp=${encodeURIComponent(_ExpCareState.curp)}&limit=1`),
      fetch(`${API}/api/legal/consent/${encodeURIComponent(_ExpCareState.curp)}`),
    ]);

    if (!pRes.ok) throw new Error('No se pudo cargar el expediente');
    const patient = await pRes.json();
    const eventsData = evRes.ok ? await evRes.json() : [];
    const events = Array.isArray(eventsData) ? eventsData : (eventsData.eventos || []);
    const vitData = vitRes.ok ? await vitRes.json() : {};
    const vitals = (vitData.readings && vitData.readings[0]) || null;
    const consentData = conRes.ok ? await conRes.json() : {};

    _ExpCareState.patient = patient;
    _ExpCareState.events = events;
    _ExpCareState.allergies = patient.alergias || [];
    _ExpCareState.vitals = vitals;

    _renderExpHeader(patient, consentData);
    _renderExpVitals(vitals);
    _renderExpHistory(events);
    _renderExpSafetyNotice();
    _loadExpAiSummary(_ExpCareState.curp, patient, events);
    _loadOrInitDraft(_ExpCareState.curp, patient, vitals);
  } catch (err) {
    showToast('Error cargando expediente: ' + err.message, 'error');
  }
}

function _renderExpHeader(p, consentData) {
  const fullName = `${p.nombres || ''} ${p.primer_apellido || ''} ${p.segundo_apellido || ''}`.trim() || p.curp;
  const words = fullName.split(/\s+/).filter(Boolean);
  const initials = words.length >= 2 ? `${words[0][0]}${words[1][0]}`.toUpperCase() : fullName.slice(0, 2).toUpperCase();

  const av = document.getElementById('exp-avatar');
  if (av) av.textContent = initials;
  const nm = document.getElementById('exp-patient-name');
  if (nm) nm.textContent = fullName;
  const meta = document.getElementById('exp-patient-meta');
  if (meta) {
    const edad = p.edad != null ? `${p.edad} años` : 'Edad N/D';
    const sexo = p.sexo || 'Sexo N/D';
    const ts = p.tipo_sangre ? ` · ${p.tipo_sangre}` : '';
    meta.textContent = `${edad} · ${sexo}${ts} · CURP: ${p.curp}`;
  }

  const triageEl = document.getElementById('exp-triage-badge');
  if (triageEl) {
    triageEl.textContent = p.programa_medico || p.tipo_paciente || 'Atención especializada';
  }

  const algEl = document.getElementById('exp-allergy-badge');
  if (algEl) {
    const algs = p.alergias || [];
    if (algs.length) {
      algEl.className = 'exp-pill exp-pill-danger';
      algEl.textContent = `Alergia: ${algs.map(a => a.descripcion).join(', ')}`;
    } else {
      algEl.className = 'exp-pill exp-pill-safe';
      algEl.textContent = 'Sin alergias registradas';
    }
  }

  const conEl = document.getElementById('exp-consent-badge');
  if (conEl) {
    const c = consentData.consent;
    const ok = !!(consentData.has_consent && c && c.status === 'active' && c.accepted_privacy_notice);
    conEl.className = ok ? 'exp-pill exp-pill-safe' : 'exp-pill exp-pill-warn';
    conEl.textContent = ok ? 'Consentimiento firmado' : 'Consentimiento pendiente';
  }
}

function _computeNews2(v) {
  if (!v) return { score: 0, label: 'Sin registro reciente' };
  let score = 0;
  const hr = Number(v.heart_rate);
  const spo2 = Number(v.spo2);
  const sbp = Number(v.systolic_bp);
  const temp = Number(v.temperature_c);

  if (hr > 0) {
    if (hr <= 40 || hr >= 131) score += 3;
    else if (hr >= 111) score += 2;
    else if (hr <= 50 || hr >= 91) score += 1;
  }
  if (spo2 > 0) {
    if (spo2 <= 91) score += 3;
    else if (spo2 <= 93) score += 2;
    else if (spo2 <= 95) score += 1;
  }
  if (sbp > 0) {
    if (sbp <= 90 || sbp >= 220) score += 3;
    else if (sbp <= 100) score += 2;
    else if (sbp <= 110) score += 1;
  }
  if (temp > 0) {
    if (temp <= 35.0) score += 3;
    else if (temp >= 39.1) score += 2;
    else if (temp <= 36.0 || temp >= 38.1) score += 1;
  }
  const level = score >= 7 ? 'ALTO (Urgencia inmediata)' : score >= 5 ? 'medio-alto' : score >= 1 ? 'bajo' : 'normal';
  return { score, label: `${score} · ${level}` };
}

function _renderExpVitals(v) {
  const fc = document.getElementById('exp-vital-fc');
  const sp = document.getElementById('exp-vital-spo2');
  const ta = document.getElementById('exp-vital-ta');
  const tm = document.getElementById('exp-vital-temp');
  const tmBox = document.getElementById('exp-vital-temp-box');
  const nw = document.getElementById('exp-news2-label');

  if (fc) fc.textContent = v && v.heart_rate ? Math.round(v.heart_rate) : '--';
  if (sp) sp.textContent = v && v.spo2 ? `${Math.round(v.spo2)}%` : '--%';
  if (ta) ta.textContent = (v && v.systolic_bp && v.diastolic_bp)
    ? `${Math.round(v.systolic_bp)}/${Math.round(v.diastolic_bp)}` : '--/--';
  if (tm) tm.textContent = v && v.temperature_c ? Number(v.temperature_c).toFixed(1) : '--';

  if (tmBox) {
    const tVal = v && v.temperature_c ? Number(v.temperature_c) : 0;
    tmBox.classList.toggle('is-warn', tVal >= 37.5 || (tVal > 0 && tVal <= 35.5));
  }
  if (nw) {
    const res = _computeNews2(v);
    nw.innerHTML = `Índice de alerta temprana (NEWS2): <strong>${_expEsc(res.label)}</strong>`;
  }
}

async function _loadExpAiSummary(curp, patient, events) {
  const ul = document.getElementById('exp-ai-summary-list');
  if (!ul) return;
  ul.innerHTML = '<li>Analizando antecedentes y consultas previas...</li>';

  const bullets = [];
  if (events.length) {
    const last = events[0];
    bullets.push(`Último evento: ${last.nombre_evento || 'Consulta general'} (${(last.fecha_creacion || '').slice(0, 10) || 'reciente'}).`);
  } else {
    bullets.push('Sin consultas previas registradas en este expediente.');
  }

  const ants = patient.antecedentes || [];
  if (ants.length) {
    bullets.push(`Antecedentes: ${ants.slice(0, 2).map(a => a.descripcion).join('; ')}.`);
  } else {
    bullets.push('Sin cirugías ni crónicos registrados.');
  }

  try {
    const res = await fetch(`${API}/api/patients/${encodeURIComponent(curp)}/summary-ia`);
    if (res.ok) {
      const data = await res.json();
      const txt = (data.resumen_ia || data.summary || '').trim();
      if (txt) {
        const cleanLines = txt
          .split(/\n+/)
          .map(s => s.replace(/^[-*•\d.]+\s*/, '').trim())
          .filter(Boolean)
          .slice(0, 3);
        if (cleanLines.length) {
          ul.innerHTML = cleanLines.map(l => `<li>${_expEsc(l)}</li>`).join('');
          return;
        }
      }
    }
  } catch (_) {}

  ul.innerHTML = bullets.map(b => `<li>${_expEsc(b)}</li>`).join('');
}

function _renderExpHistory(events) {
  const box = document.getElementById('exp-history-list');
  if (!box) return;
  if (!events.length) {
    box.innerHTML = '<div style="font-size:12px; color:#64748b;">Sin historial clínico previo.</div>';
    return;
  }
  box.innerHTML = events.slice(0, 6).map(ev => {
    const rawDate = (ev.fecha_creacion || ev.created_at || '').slice(0, 10);
    const label = rawDate || 'Reciente';
    return `<div class="exp-hist-row">
      <strong>${_expEsc(label)}</strong> · <span>${_expEsc(ev.nombre_evento || 'Atención médica')}</span>
    </div>`;
  }).join('');
}

function _loadOrInitDraft(curp, patient, vitals) {
  const key = `medicaition_exp_draft_${curp}`;
  try {
    const raw = localStorage.getItem(key);
    if (raw) {
      const saved = JSON.parse(raw);
      _ExpCareState.soap = saved.soap || _ExpCareState.soap;
      _ExpCareState.meds = saved.meds || [];
      _ExpCareState.selectedLabs = new Set(saved.selectedLabs || []);
      _renderExpSoap();
      _renderExpMeds();
      _renderExpLabs();
      return;
    }
  } catch (_) {}

  const edadTxt = patient.edad != null ? `${patient.edad} años` : 'edad no especificada';
  const sexoTxt = (patient.sexo || 'paciente').toLowerCase();
  const vitStr = vitals
    ? `FC ${vitals.heart_rate || '--'}, TA ${vitals.systolic_bp || '--'}/${vitals.diastolic_bp || '--'}, Temp ${vitals.temperature_c || '--'} °C, SpO2 ${vitals.spo2 || '--'}%. `
    : '';

  _ExpCareState.soap = {
    s: `Paciente ${sexoTxt} de ${edadTxt} acude a valoración especializada. [PENDIENTE: motivo y evolución].`,
    o: `${vitStr}[PENDIENTE: hallazgos de la exploración física].`,
    a: `[PENDIENTE: impresión diagnóstica y código CIE-10 a confirmar por el médico].`,
    p: `[PENDIENTE: plan y tratamiento].`,
  };
  _ExpCareState.meds = [];
  _ExpCareState.selectedLabs = new Set();
  _renderExpSoap();
  _renderExpMeds();
  _renderExpLabs();
}

function _renderExpSoap() {
  const ed = _ExpCareState.editMode;
  ['s', 'o', 'a', 'p'].forEach(k => {
    const txtEl = document.getElementById(`exp-soap-text-${k}`);
    const inpEl = document.getElementById(`exp-soap-input-${k}`);
    if (txtEl) {
      txtEl.textContent = _ExpCareState.soap[k] || '';
      txtEl.style.display = ed ? 'none' : 'block';
    }
    if (inpEl) {
      inpEl.value = _ExpCareState.soap[k] || '';
      inpEl.style.display = ed ? 'block' : 'none';
    }
  });
  const btn = document.getElementById('exp-btn-edit-soap');
  if (btn) btn.textContent = ed ? 'Guardar cambios de nota' : 'Editar nota';
}

function toggleExpEditMode() {
  if (_ExpCareState.editMode) {
    ['s', 'o', 'a', 'p'].forEach(k => {
      const inp = document.getElementById(`exp-soap-input-${k}`);
      if (inp) _ExpCareState.soap[k] = inp.value.trim();
    });
    _ExpCareState.editMode = false;
    _renderExpSoap();
    showToast('Nota SOAP actualizada', 'success');
  } else {
    _ExpCareState.editMode = true;
    _renderExpSoap();
  }
}

function toggleExpDictation() {
  const badge = document.getElementById('exp-dictation-badge');
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (_ExpCareState.isDictating && _ExpCareState.recognition) {
    _ExpCareState.recognition.stop();
    _ExpCareState.isDictating = false;
    if (badge) {
      badge.classList.remove('is-live');
      badge.textContent = '● LISTO PARA DICTADO';
    }
    return;
  }

  if (SpeechRec) {
    const rec = new SpeechRec();
    rec.lang = 'es-MX';
    rec.continuous = true;
    rec.interimResults = false;
    rec.onresult = (ev) => {
      const transcript = Array.from(ev.results).slice(ev.resultIndex).map(r => r[0].transcript).join(' ').trim();
      if (!transcript) return;
      if (_ExpCareState.soap.s.includes('[PENDIENTE')) {
        _ExpCareState.soap.s = transcript;
      } else {
        _ExpCareState.soap.s += ' ' + transcript;
      }
      _renderExpSoap();
    };
    rec.onerror = () => {
      _ExpCareState.isDictating = false;
      if (badge) {
        badge.classList.remove('is-live');
        badge.textContent = '● LISTO PARA DICTADO';
      }
    };
    rec.start();
    _ExpCareState.recognition = rec;
    _ExpCareState.isDictating = true;
    if (badge) {
      badge.classList.add('is-live');
      badge.textContent = '● GRABANDO';
    }
    showToast('🎙️ Dictado activo en español médico (es-MX)', 'info');
  } else {
    // Fallback offline si el navegador no soporta Web Speech API
    _ExpCareState.editMode = true;
    _renderExpSoap();
    showToast('Dictado por micrófono no disponible en este navegador; modo edición habilitado.', 'info');
  }
}

async function suggestExpCie10() {
  if (!_ExpCareState.curp) return;
  const text = `${_ExpCareState.soap.s} ${_ExpCareState.soap.o} ${_ExpCareState.soap.a}`.trim();
  try {
    const fd = new FormData();
    fd.append('text', text);
    fd.append('curp', _ExpCareState.curp);
    fd.append('llm_mode', 'local');
    const res = await fetch(`${API}/api/input/text`, { method: 'POST', body: fd });
    if (!res.ok) throw new Error(await res.text());
    const data = await res.json();
    const dxList = data.entidades?.diagnosticos || data.nota_medica?.diagnosticos_cie10 || [];
    if (dxList.length) {
      const top = dxList[0];
      const code = top.codigo_cie10 || top.code || '';
      const desc = top.descripcion || top.nombre || top.diagnostico || '';
      _ExpCareState.soap.a = `${desc}${code ? ` — Sugerencia CIE-10: ${code}` : ''}, a confirmar por el médico.`;
      _renderExpSoap();
      showToast(`Sugerencia CIE-10 aplicada: ${code || desc}`, 'success');
    } else {
      showToast('No se detectó un diagnóstico específico aún. Completa la sección S o A.', 'info');
    }
  } catch (err) {
    showToast('No se pudo sugerir CIE-10: ' + err.message, 'error');
  }
}

function addExpMedication() {
  const nameEl = document.getElementById('exp-med-search');
  const doseEl = document.getElementById('exp-med-dose');
  const nombre = nameEl?.value?.trim();
  if (!nombre) return showToast('Escribe el nombre del medicamento', 'error');
  const dosis = doseEl?.value?.trim() || 'Según indicación';

  _ExpCareState.meds.push({
    nombre,
    dosis,
    via: 'Oral',
    periodicidad: 'cada 8 horas',
    duracion: 'por 5 días',
  });
  if (nameEl) nameEl.value = '';
  if (doseEl) doseEl.value = '';
  _renderExpMeds();
  _renderExpSafetyNotice();
}

function removeExpMedication(idx) {
  _ExpCareState.meds.splice(idx, 1);
  _renderExpMeds();
  _renderExpSafetyNotice();
}

function _renderExpMeds() {
  const box = document.getElementById('exp-meds-list');
  if (!box) return;
  if (!_ExpCareState.meds.length) {
    box.innerHTML = '';
    return;
  }
  box.innerHTML = _ExpCareState.meds.map((m, i) => `
    <div class="exp-med-item">
      <div><strong>${_expEsc(m.nombre)}</strong> <small>${_expEsc(m.dosis)} · ${_expEsc(m.periodicidad)}</small></div>
      <button type="button" onclick="removeExpMedication(${i})" title="Quitar">✕</button>
    </div>
  `).join('');
}

function _renderExpSafetyNotice() {
  const box = document.getElementById('exp-safety-warning');
  if (!box) return;
  const algs = _ExpCareState.allergies || [];
  if (!algs.length) {
    box.className = 'exp-safety-box safe';
    box.innerHTML = '<strong>Verificación farmacológica activa:</strong> sin alergias registradas; el sistema validará interacciones antes de firmar.';
    return;
  }
  const algNames = algs.map(a => a.descripcion).join(', ');
  const penAllergy = /penicil|betalact/i.test(algNames);
  const conflict = _ExpCareState.meds.some(m => {
    const mn = m.nombre.toLowerCase();
    return algs.some(a => mn.includes((a.descripcion || '').toLowerCase())) ||
      (penAllergy && /(amoxicil|ampicil|penicil|dicloxacil)/i.test(mn));
  });

  box.className = conflict ? 'exp-safety-box critical' : 'exp-safety-box';
  box.innerHTML = conflict
    ? `<strong>🚨 ALERTA DE SEGURIDAD:</strong> Posible reacción cruzada con alergia registrada (<strong>${_expEsc(algNames)}</strong>). Cambia el medicamento antes de firmar.`
    : `<strong>Aviso de seguridad:</strong> el paciente tiene alergia registrada a <strong>${_expEsc(algNames)}</strong>. El sistema revisará alergias e interacciones antes de firmar.`;
}

function toggleExpLabChip(name) {
  if (_ExpCareState.selectedLabs.has(name)) {
    _ExpCareState.selectedLabs.delete(name);
  } else {
    _ExpCareState.selectedLabs.add(name);
  }
  _renderExpLabs();
}

function addCustomExpLab() {
  const custom = prompt('Nombre de estudio de laboratorio o imagen:');
  if (!custom || !custom.trim()) return;
  const clean = custom.trim();
  _ExpCareState.labs.add(clean);
  _ExpCareState.selectedLabs.add(clean);
  _renderExpLabs();
}

function _renderExpLabs() {
  const wrap = document.getElementById('exp-labs-chips');
  if (!wrap) return;
  const chips = [..._ExpCareState.labs].map(name => {
    const active = _ExpCareState.selectedLabs.has(name);
    return `<button type="button" class="exp-lab-chip ${active ? 'active' : ''}" onclick="toggleExpLabChip('${_expEsc(name)}')">${_expEsc(name)}</button>`;
  }).join('');
  wrap.innerHTML = `${chips}<button type="button" class="exp-lab-chip add" onclick="addCustomExpLab()">+ Otra orden</button>`;
}

function toggleExpQuickVitalsForm() {
  const box = document.getElementById('exp-quick-vitals-form');
  if (!box) return;
  box.style.display = box.style.display === 'none' ? 'grid' : 'none';
}

async function saveExpQuickVitals() {
  if (!_ExpCareState.curp) return;
  const payload = {
    curp: _ExpCareState.curp,
    heart_rate: parseFloat(document.getElementById('exp-qv-hr')?.value) || null,
    spo2: parseFloat(document.getElementById('exp-qv-spo2')?.value) || null,
    systolic_bp: parseFloat(document.getElementById('exp-qv-sbp')?.value) || null,
    diastolic_bp: parseFloat(document.getElementById('exp-qv-dbp')?.value) || null,
    temperature_c: parseFloat(document.getElementById('exp-qv-temp')?.value) || null,
    source: 'manual',
  };
  try {
    const res = await fetch(`${API}/api/wearables/readings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const out = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(out.detail || 'Error al guardar vitales');
    document.getElementById('exp-quick-vitals-form').style.display = 'none';
    await loadSpecializedPatient(_ExpCareState.curp);
    showToast('✅ Signos vitales actualizados y evaluados con NEWS2', 'success');
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function saveExpDraft() {
  if (!_ExpCareState.curp) return;
  if (_ExpCareState.editMode) toggleExpEditMode();
  try {
    localStorage.setItem(`medicaition_exp_draft_${_ExpCareState.curp}`, JSON.stringify({
      soap: _ExpCareState.soap,
      meds: _ExpCareState.meds,
      selectedLabs: [..._ExpCareState.selectedLabs],
    }));
    showToast('💾 Borrador guardado localmente para este paciente', 'success');
  } catch (e) {
    showToast('No se pudo guardar borrador', 'error');
  }
}

async function signAndCloseSpecializedConsult() {
  if (!_ExpCareState.curp) return showToast('Selecciona un paciente primero', 'error');
  if (_ExpCareState.editMode) toggleExpEditMode();

  try {
    // 1. Obtener o crear evento clínico activo
    let eventoId = _ExpCareState.events[0]?.id;
    if (!eventoId) {
      const evRes = await fetch(`${API}/api/patients/${encodeURIComponent(_ExpCareState.curp)}/events`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          nombre_evento: 'Atención Especializada',
          doctor_creador: AppState.operatorProfile?.full_name || 'Médico',
        }),
      });
      if (!evRes.ok) throw new Error((await evRes.json().catch(() => ({}))).detail || 'Error creando evento clínico');
      eventoId = (await evRes.json()).id;
    }

    const labsArr = [..._ExpCareState.selectedLabs];
    const follow7d = !!document.getElementById('exp-follow-7d')?.checked;
    const followWa = !!document.getElementById('exp-follow-whatsapp')?.checked;
    const followAl = !!document.getElementById('exp-follow-alarm')?.checked;

    const res = await fetch(`${API}/api/consultations/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        evento_id: eventoId,
        doctor_nombre: AppState.operatorProfile?.full_name || 'Dr. Roberto Morales',
        texto_original: `S: ${_ExpCareState.soap.s}\nO: ${_ExpCareState.soap.o}\nA: ${_ExpCareState.soap.a}\nP: ${_ExpCareState.soap.p}`,
        nota_medica: {
          motivo_consulta: _ExpCareState.soap.s,
          exploracion_fisica: _ExpCareState.soap.o,
          diagnostico_integral: _ExpCareState.soap.a,
          plan_tratamiento: _ExpCareState.soap.p,
          ordenes_estudios: labsArr,
          seguimiento: { revision_7_dias: follow7d, recordatorio: followWa, alarma_por_escrito: followAl },
        },
        receta: {
          medicamentos: _ExpCareState.meds,
          instrucciones: _ExpCareState.soap.p,
        },
        entidades: {
          ordenes_laboratorio_imagen: labsArr,
        },
      }),
    });
    const out = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(out.detail || 'No se pudo firmar la consulta');

    if (follow7d) {
      const nextDate = new Date(Date.now() + 7 * 86400000).toISOString().slice(0, 10);
      await fetch(`${API}/api/appointments/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          patient_curp: _ExpCareState.curp,
          patient_name: document.getElementById('exp-patient-name')?.textContent || _ExpCareState.curp,
          date_str: nextDate,
          time_str: '10:00',
          reason: 'Revisión de seguimiento (7 días)',
          doctor_nombre: AppState.operatorProfile?.full_name || 'Médico',
        }),
      }).catch(() => {});
    }

    localStorage.removeItem(`medicaition_exp_draft_${_ExpCareState.curp}`);
    showToast('✅ Consulta firmada NOM-004, cifrada y sellada en bitácora', 'success');
    await loadSpecializedPatient(_ExpCareState.curp);
  } catch (err) {
    showToast(err.message, 'error');
  }
}

function _startExpTimer() {
  if (_ExpCareState.timerInterval) return;
  _ExpCareState.timerInterval = setInterval(() => {
    if (AppState.mainTab !== 'expediente' || _ExpCareState.timerPaused) return;
    _ExpCareState.timerSeconds += 1;
    const h = String(Math.floor(_ExpCareState.timerSeconds / 3600)).padStart(2, '0');
    const m = String(Math.floor((_ExpCareState.timerSeconds % 3600) / 60)).padStart(2, '0');
    const s = String(_ExpCareState.timerSeconds % 60).padStart(2, '0');
    const el = document.getElementById('exp-timer-display');
    if (el) el.textContent = `${h}:${m}:${s}`;
  }, 1000);
}

function toggleExpTimer() {
  _ExpCareState.timerPaused = !_ExpCareState.timerPaused;
  const btn = document.getElementById('exp-timer-toggle');
  if (btn) btn.textContent = _ExpCareState.timerPaused ? 'Reanudar' : 'Pausar';
}
