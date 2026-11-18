// ============================================================================
// premium_search.js — MedicAItion v3.0
// ============================================================================
// Sistema de Búsqueda Premium, Semántica & Command Palette (OmniSearch Spotlight)
// - Atajo global Ctrl+K / Cmd+K / "/"
// - Búsqueda híbrida ultrarrápida: Caché local (<1ms) + Vector Semántico ChromaDB
// - Búsqueda por Nombre, CURP, Folio, Especialidad, Diagnóstico CIE-10, Síntomas
// - Combobox Inteligente y Estilizado que reemplaza selects nativos de pacientes
// ============================================================================

(function () {
  'use strict';

  const OmniSearchState = {
    isOpen: false,
    query: '',
    filterCategory: 'all', // all, cardio, neumo, endocrino, alergias, urgencias
    selectedIndex: 0,
    results: [],
    patientsCache: [],
    recentSearches: [],
    debounceTimer: null,
    isSemanticSearching: false
  };

  // Helper para escapar HTML
  function _esc(str) {
    if (str == null) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  // Resaltado de texto coincidente
  function _highlight(text, query) {
    if (!text) return '';
    if (!query || !query.trim()) return _esc(text);
    const escapedText = _esc(text);
    const cleanQ = query.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`(${cleanQ})`, 'gi');
    return escapedText.replace(regex, '<mark class="omni-highlight">$1</mark>');
  }

  // Cargar pacientes en caché si no están disponibles
  async function _ensurePatientsCache() {
    if (OmniSearchState.patientsCache && OmniSearchState.patientsCache.length > 0) {
      return OmniSearchState.patientsCache;
    }
    try {
      if (window.AppState && Array.isArray(window.AppState.allPatients) && window.AppState.allPatients.length > 0) {
        OmniSearchState.patientsCache = window.AppState.allPatients;
        return OmniSearchState.patientsCache;
      }
      const res = await fetch('/api/patients/');
      if (res.ok) {
        const data = await res.json();
        OmniSearchState.patientsCache = Array.isArray(data) ? data : (data.patients || []);
        if (window.AppState) window.AppState.allPatients = OmniSearchState.patientsCache;
      }
    } catch (e) {
      console.warn('[OmniSearch] Error cargando caché de pacientes:', e);
    }
    return OmniSearchState.patientsCache || [];
  }

  // Extraer iniciales para el avatar
  function _getInitials(name) {
    if (!name) return 'PT';
    const parts = name.trim().split(/\s+/).filter(Boolean);
    if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
    return (parts[0][0] + (parts[1] ? parts[1][0] : '')).toUpperCase();
  }

  // ==========================================================================
  // INYECCIÓN DEL MODAL SPOTLIGHT (COMMAND PALETTE)
  // ==========================================================================
  function _injectSpotlightModal() {
    if (document.getElementById('omni-search-modal')) return;

    const modal = document.createElement('div');
    modal.id = 'omni-search-modal';
    modal.className = 'omni-modal-overlay';
    modal.style.display = 'none';

    modal.innerHTML = `
      <div class="omni-backdrop" onclick="OmniSearch.close()"></div>
      <div class="omni-dialog" role="dialog" aria-modal="true" aria-label="Buscador Inteligente de Pacientes">
        
        <!-- HEADER / INPUT -->
        <div class="omni-header">
          <div class="omni-input-wrapper">
            <svg class="omni-search-icon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2">
              <circle cx="11" cy="11" r="8"></circle>
              <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
            </svg>
            <input 
              type="text" 
              id="omni-search-input" 
              class="omni-search-input" 
              placeholder="Buscar por paciente, CURP, síntoma, enfermedad o CIE-10..." 
              autocomplete="off"
              spellcheck="false"
            />
            <button type="button" class="omni-clear-btn" id="omni-clear-btn" onclick="OmniSearch.clearInput()" style="display:none;" title="Limpiar búsqueda">✕</button>
            <div class="omni-kbd-badge"><kbd>ESC</kbd></div>
          </div>

          <!-- CATEGORY FILTERS CHIPS -->
          <div class="omni-filters-bar">
            <button type="button" class="omni-filter-chip active" data-cat="all" onclick="OmniSearch.setCategory('all')">
              Todos <span class="chip-count" id="omni-count-all">25</span>
            </button>
            <button type="button" class="omni-filter-chip" data-cat="cardio" onclick="OmniSearch.setCategory('cardio')">
              🫀 Cardio
            </button>
            <button type="button" class="omni-filter-chip" data-cat="neumo" onclick="OmniSearch.setCategory('neumo')">
              🫁 Neumo
            </button>
            <button type="button" class="omni-filter-chip" data-cat="endocrino" onclick="OmniSearch.setCategory('endocrino')">
              🩸 Endocrino
            </button>
            <button type="button" class="omni-filter-chip" data-cat="alergias" onclick="OmniSearch.setCategory('alergias')">
              ⚠️ Alergias Críticas
            </button>
            <button type="button" class="omni-filter-chip" data-cat="urgencias" onclick="OmniSearch.setCategory('urgencias')">
              🚨 Triaje Alto
            </button>
          </div>
        </div>

        <!-- BODY / RESULTS CONTAINER -->
        <div class="omni-body">
          <div class="omni-status-bar" id="omni-status-bar">
            <span id="omni-status-text">Pacientes recientes y frecuentes</span>
            <span id="omni-semantic-indicator" class="omni-semantic-indicator" style="display:none;">
              <span class="omni-ai-sparkle">✨</span> Motor Semántico IA Activo
            </span>
          </div>
          <div class="omni-results-list" id="omni-results-list" tabindex="0">
            <!-- Dynamic Results -->
          </div>
        </div>

        <!-- FOOTER / SHORTCUTS HINTS -->
        <div class="omni-footer">
          <div class="omni-footer-hints">
            <span><kbd>↑</kbd> <kbd>↓</kbd> Navegar</span>
            <span><kbd>↵</kbd> Ver Expediente</span>
            <span><kbd>Ctrl</kbd> + <kbd>↵</kbd> Nueva Consulta</span>
            <span><kbd>ESC</kbd> Cerrar</span>
          </div>
          <div class="omni-footer-meta">
            <span>Directorio Clínico · NOM-004 / NOM-024</span>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(modal);

    // Event listeners en el input del modal
    const input = document.getElementById('omni-search-input');
    input.addEventListener('input', (e) => {
      OmniSearch.onInputChange(e.target.value);
    });

    input.addEventListener('keydown', (e) => {
      OmniSearch.onKeyDown(e);
    });
  }

  // ==========================================================================
  // FILTRADO INTELIGENTE (LOCAL + SEMÁNTICO)
  // ==========================================================================
  function _filterPatients(patients, query, category) {
    if (!Array.isArray(patients)) return [];

    let filtered = patients;

    // Filtro por categoría rápida
    if (category && category !== 'all') {
      filtered = filtered.filter(p => {
        const text = `${p.anotaciones_generales || ''} ${p.resumen_ia || ''} ${JSON.stringify(p.alergias || [])}`.toLowerCase();
        if (category === 'cardio') return text.includes('cardio') || text.includes('hipertens') || text.includes('insuficiencia') || text.includes('coraz');
        if (category === 'neumo') return text.includes('neumo') || text.includes('asma') || text.includes('epoc') || text.includes('pulmon');
        if (category === 'endocrino') return text.includes('diabetes') || text.includes('tiroid') || text.includes('hashimoto') || text.includes('metabol');
        if (category === 'alergias') return (Array.isArray(p.alergias) && p.alergias.length > 0) || text.includes('alergia') || text.includes('penicilina');
        if (category === 'urgencias') return text.includes('aguda') || text.includes('apendicitis') || text.includes('alarma') || text.includes('dengue');
        return true;
      });
    }

    if (!query || !query.trim()) {
      return filtered;
    }

    const cleanQ = query.trim().toLowerCase();
    const tokens = cleanQ.split(/\s+/).filter(Boolean);

    return filtered.filter(p => {
      const name = `${p.nombres || ''} ${p.primer_apellido || ''} ${p.segundo_apellido || ''}`.toLowerCase();
      const curp = (p.curp || '').toLowerCase();
      const rfc = (p.rfc || '').toLowerCase();
      const folio = (p.folio_hospital || '').toLowerCase();
      const notes = (p.anotaciones_generales || '').toLowerCase();
      const city = (p.ubicacion_casa || p.lugar_nacimiento || '').toLowerCase();
      const email = (p.email || '').toLowerCase();

      const composite = `${name} ${curp} ${rfc} ${folio} ${notes} ${city} ${email}`;
      return tokens.every(tok => composite.includes(tok));
    });
  }

  // ==========================================================================
  // RENDERIZADO DE RESULTADOS EN EL SPOTLIGHT
  // ==========================================================================
  function _renderResults() {
    const container = document.getElementById('omni-results-list');
    const statusBar = document.getElementById('omni-status-text');
    const clearBtn = document.getElementById('omni-clear-btn');
    if (!container) return;

    const query = OmniSearchState.query;
    if (clearBtn) clearBtn.style.display = query ? 'block' : 'none';

    const results = OmniSearchState.results;

    if (!results || results.length === 0) {
      if (statusBar) statusBar.textContent = `No se hallaron resultados para "${query}"`;
      container.innerHTML = `
        <div class="omni-empty-state">
          <div class="omni-empty-icon">🔍</div>
          <div class="omni-empty-title">Sin coincidencias clínicas directas</div>
          <div class="omni-empty-desc">
            Prueba buscando por síntomas ("dificultad respiratoria", "fiebre", "dolor lumbar"), códigos CIE-10 (ej: E11, J45) o apellidos.
          </div>
        </div>
      `;
      return;
    }

    if (statusBar) {
      const total = OmniSearchState.patientsCache.length || results.length;
      statusBar.textContent = query
        ? `Se encontraron ${results.length} expediente(s) para "${query}"`
        : `Mostrando ${results.length} pacientes disponibles (${total} en total)`;
    }

    // Asegurar que selectedIndex sea válido
    if (OmniSearchState.selectedIndex >= results.length) {
      OmniSearchState.selectedIndex = 0;
    }

    container.innerHTML = results.map((p, idx) => {
      const isSelected = idx === OmniSearchState.selectedIndex;
      const curp = p.curp || p.patient_curp || '';
      const name = p.nombre_completo || p.nombre || `${p.nombres || ''} ${p.primer_apellido || ''} ${p.segundo_apellido || ''}`.trim() || curp;
      const initials = _getInitials(name);
      const age = p.edad != null ? `${p.edad} años` : (p.fecha_nacimiento ? `${p.fecha_nacimiento}` : '');
      const blood = p.tipo_sangre ? `Sangre ${p.tipo_sangre}` : '';
      const gender = p.sexo === 'M' ? 'Masc.' : (p.sexo === 'F' ? 'Fem.' : '');
      const notes = p.anotaciones_generales || p.diagnostico || '';
      const cie10 = p.cie10 || (notes.match(/[A-Z]\d{2}(?:\.\d+)?/g) ? notes.match(/[A-Z]\d{2}(?:\.\d+)?/g)[0] : '');
      const isAiMatch = p.similitud != null;
      const aiScore = isAiMatch ? Math.round(p.similitud * 100) : null;

      // Alergias
      let allergyPill = '';
      if (Array.isArray(p.alergias) && p.alergias.length > 0) {
        allergyPill = `<span class="omni-allergy-chip" title="${_esc(p.alergias[0].descripcion || 'Alergia')}">⚠️ ${p.alergias.length} alergia(s)</span>`;
      }

      return `
        <div 
          class="omni-result-item ${isSelected ? 'is-selected' : ''}" 
          data-index="${idx}"
          data-curp="${_esc(curp)}"
          onclick="OmniSearch.selectPatient('${_esc(curp)}', 'expediente')"
          onmouseenter="OmniSearch.setSelectedIndex(${idx})"
        >
          <div class="omni-item-avatar">${_esc(initials)}</div>
          
          <div class="omni-item-content">
            <div class="omni-item-top">
              <span class="omni-item-name">${_highlight(name, query)}</span>
              <span class="omni-item-curp-badge">${_highlight(curp, query)}</span>
              ${aiScore ? `<span class="omni-ai-badge">IA: ${aiScore}% match</span>` : ''}
            </div>

            <div class="omni-item-meta">
              ${age ? `<span>👤 ${age}</span>` : ''}
              ${gender ? `<span>• ${gender}</span>` : ''}
              ${blood ? `<span>• 🩸 ${blood}</span>` : ''}
              ${allergyPill}
            </div>

            ${notes ? `
              <div class="omni-item-diagnosis">
                ${cie10 ? `<span class="omni-cie10-pill">${cie10}</span>` : ''}
                <span class="omni-diagnosis-text">${_highlight(notes, query)}</span>
              </div>
            ` : ''}
          </div>

          <!-- BOTONES DE ACCIÓN RÁPIDA -->
          <div class="omni-item-actions" onclick="event.stopPropagation()">
            <button type="button" class="omni-action-btn" onclick="OmniSearch.selectPatient('${_esc(curp)}', 'dashboard')" title="Ver telemetría y signos vitales">
              📊 Resumen
            </button>
            <button type="button" class="omni-action-btn primary" onclick="OmniSearch.selectPatient('${_esc(curp)}', 'expediente')" title="Abrir expediente clínico completo">
              📋 Expediente
            </button>
            <button type="button" class="omni-action-btn" onclick="OmniSearch.selectPatient('${_esc(curp)}', 'consulta')" title="Iniciar nueva consulta médica">
              🩺 Consulta
            </button>
          </div>
        </div>
      `;
    }).join('');

    // Auto-scroll al elemento seleccionado
    const selectedEl = container.querySelector('.omni-result-item.is-selected');
    if (selectedEl) {
      selectedEl.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    }
  }

  // ==========================================================================
  // DISPATCHER DE BÚSQUEDA HÍBRIDA
  // ==========================================================================
  async function _executeSearch() {
    await _ensurePatientsCache();
    const query = OmniSearchState.query.trim();
    const category = OmniSearchState.filterCategory;

    // 1. Filtrado local instantáneo (< 1ms)
    const localMatches = _filterPatients(OmniSearchState.patientsCache, query, category);
    OmniSearchState.results = localMatches;
    OmniSearchState.selectedIndex = 0;
    _renderResults();

    // 2. Si la consulta tiene más de 3 letras, activar paralelamente la Búsqueda Semántica Vectorial
    const semanticIndicator = document.getElementById('omni-semantic-indicator');
    if (query.length >= 3) {
      clearTimeout(OmniSearchState.debounceTimer);
      OmniSearchState.debounceTimer = setTimeout(async () => {
        try {
          if (semanticIndicator) semanticIndicator.style.display = 'inline-flex';
          const res = await fetch(`/api/patients/search/semantic?q=${encodeURIComponent(query)}`);
          if (res.ok) {
            const semanticData = await res.json();
            if (Array.isArray(semanticData) && semanticData.length > 0) {
              // Combinar resultados semánticos con locales sin duplicados
              const existingCurps = new Set(localMatches.map(p => p.curp || p.patient_curp));
              const extraMatches = [];
              
              for (const semItem of semanticData) {
                const sCurp = semItem.patient_curp || semItem.curp;
                if (!existingCurps.has(sCurp)) {
                  // Buscar el objeto completo en la caché local
                  const fullObj = OmniSearchState.patientsCache.find(p => p.curp === sCurp);
                  if (fullObj) {
                    extraMatches.push({
                      ...fullObj,
                      similitud: semItem.similitud,
                      anotaciones_generales: semItem.match_text || fullObj.anotaciones_generales
                    });
                  } else {
                    extraMatches.push(semItem);
                  }
                  existingCurps.add(sCurp);
                } else {
                  // Enriquecer el objeto existente con el score semántico
                  const found = localMatches.find(p => (p.curp || p.patient_curp) === sCurp);
                  if (found) found.similitud = semItem.similitud;
                }
              }

              // Ordenar: primero los de mayor relevancia
              OmniSearchState.results = [...localMatches, ...extraMatches].sort((a, b) => {
                const simA = a.similitud || 0;
                const simB = b.similitud || 0;
                return simB - simA;
              });
              _renderResults();
            }
          }
        } catch (e) {
          console.warn('[OmniSearch] Error en búsqueda semántica:', e);
        } finally {
          if (semanticIndicator) semanticIndicator.style.display = 'none';
        }
      }, 260);
    } else {
      if (semanticIndicator) semanticIndicator.style.display = 'none';
    }
  }

  // ==========================================================================
  // COMBOBOX MODERNO (REEMPLAZO DEL SELECT NATIVO)
  // ==========================================================================
  function _upgradeNativeSelectToCombobox(selectId, onSelectCallback) {
    const rawSelect = document.getElementById(selectId);
    if (!rawSelect) return;

    // Verificar si ya fue enriquecido
    const existingWrapper = document.getElementById(`${selectId}-combobox-wrap`);
    if (existingWrapper) {
      _refreshComboboxData(selectId);
      return;
    }

    // Ocultar el select nativo pero mantenerlo accesible para formularios legacy
    rawSelect.style.display = 'none';

    // Crear el contenedor combobox
    const wrap = document.createElement('div');
    wrap.id = `${selectId}-combobox-wrap`;
    wrap.className = 'premium-combobox-wrapper';

    wrap.innerHTML = `
      <button type="button" class="combobox-trigger-btn" id="${selectId}-btn" onclick="OmniSearch.toggleCombobox('${selectId}')" aria-haspopup="listbox" aria-expanded="false">
        <span class="combobox-avatar" id="${selectId}-btn-avatar">--</span>
        <div class="combobox-label-group">
          <span class="combobox-name" id="${selectId}-btn-name">Seleccionar paciente...</span>
          <span class="combobox-curp" id="${selectId}-btn-curp">---</span>
        </div>
        <svg class="combobox-chevron" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
          <polyline points="6 9 12 15 18 9"></polyline>
        </svg>
      </button>

      <!-- DROPDOWN POPOVER -->
      <div class="combobox-dropdown" id="${selectId}-dropdown" style="display:none;" role="listbox">
        <div class="combobox-search-box">
          <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <input 
            type="text" 
            class="combobox-search-input" 
            id="${selectId}-filter-input" 
            placeholder="Escribe para filtrar (nombre, CURP, enfermedad)..." 
            oninput="OmniSearch.filterCombobox('${selectId}', this.value)"
          />
        </div>
        <div class="combobox-items-container" id="${selectId}-items-container">
          <!-- Items generados dinámicamente -->
        </div>
        <div class="combobox-footer">
          <button type="button" class="combobox-open-spotlight-link" onclick="OmniSearch.open()">
            ✨ Abrir Buscador Avanzado (Ctrl+K)
          </button>
        </div>
      </div>
    `;

    rawSelect.parentNode.insertBefore(wrap, rawSelect.nextSibling);

    // Llenar datos iniciales
    _refreshComboboxData(selectId, onSelectCallback);

    // Cerrar al hacer clic afuera
    document.addEventListener('click', (e) => {
      if (!wrap.contains(e.target)) {
        const dd = document.getElementById(`${selectId}-dropdown`);
        const btn = document.getElementById(`${selectId}-btn`);
        if (dd && dd.style.display !== 'none') {
          dd.style.display = 'none';
          if (btn) btn.setAttribute('aria-expanded', 'false');
        }
      }
    });
  }

  function _refreshComboboxData(selectId, onSelectCallback) {
    const rawSelect = document.getElementById(selectId);
    const container = document.getElementById(`${selectId}-items-container`);
    if (!rawSelect || !container) return;

    const patients = OmniSearchState.patientsCache;
    const selectedCurp = rawSelect.value;

    let selectedPatient = patients.find(p => p.curp === selectedCurp);
    if (!selectedPatient && patients.length > 0) {
      selectedPatient = patients[0];
    }

    _updateComboboxTrigger(selectId, selectedPatient);

    // Renderizar opciones
    container.innerHTML = patients.map(p => {
      const name = `${p.nombres || ''} ${p.primer_apellido || ''} ${p.segundo_apellido || ''}`.trim() || p.curp;
      const initials = _getInitials(name);
      const isSelected = selectedPatient && selectedPatient.curp === p.curp;
      const disease = p.anotaciones_generales ? p.anotaciones_generales.split('-')[0].replace('Diagnóstico clínico principal:', '').trim() : '';

      return `
        <div 
          class="combobox-item ${isSelected ? 'is-selected' : ''}" 
          data-curp="${_esc(p.curp)}"
          data-text="${_esc(name)} ${_esc(p.curp)} ${_esc(disease)}".toLowerCase()
          onclick="OmniSearch.chooseComboboxOption('${selectId}', '${_esc(p.curp)}')"
        >
          <span class="combobox-item-avatar">${_esc(initials)}</span>
          <div class="combobox-item-info">
            <span class="combobox-item-name">${_esc(name)}</span>
            <span class="combobox-item-meta">${_esc(p.curp)} ${p.edad ? `· ${p.edad} años` : ''}</span>
            ${disease ? `<span class="combobox-item-disease">${_esc(disease)}</span>` : ''}
          </div>
          ${isSelected ? '<span class="combobox-checkmark">✓</span>' : ''}
        </div>
      `;
    }).join('');
  }

  function _updateComboboxTrigger(selectId, patient) {
    const btnAvatar = document.getElementById(`${selectId}-btn-avatar`);
    const btnName = document.getElementById(`${selectId}-btn-name`);
    const btnCurp = document.getElementById(`${selectId}-btn-curp`);

    if (!patient) {
      if (btnName) btnName.textContent = 'Seleccionar paciente...';
      if (btnCurp) btnCurp.textContent = '---';
      if (btnAvatar) btnAvatar.textContent = '--';
      return;
    }

    const name = `${patient.nombres || ''} ${patient.primer_apellido || ''} ${patient.segundo_apellido || ''}`.trim() || patient.curp;
    if (btnName) btnName.textContent = name;
    if (btnCurp) btnCurp.textContent = patient.curp;
    if (btnAvatar) btnAvatar.textContent = _getInitials(name);
  }

  // ==========================================================================
  // API PÚBLICA DEL MOTOR DE BÚSQUEDA
  // ==========================================================================
  window.OmniSearch = {
    upgradeSelect(selectId, onSelectCallback) {
      _upgradeNativeSelectToCombobox(selectId, onSelectCallback);
    },
    async init() {
      _injectSpotlightModal();
      await _ensurePatientsCache();

      // Enlazar barra de búsqueda del topbar para abrir Spotlight
      const topbarSearch = document.getElementById('global-quick-search');
      if (topbarSearch) {
        topbarSearch.setAttribute('readonly', 'true');
        topbarSearch.style.cursor = 'pointer';
        topbarSearch.placeholder = 'Buscar paciente o enfermedad (Ctrl+K)...';
        topbarSearch.onclick = () => OmniSearch.open();
        topbarSearch.onfocus = () => {
          topbarSearch.blur();
          OmniSearch.open();
        };
      }

      // Atajos de teclado globales
      window.addEventListener('keydown', (e) => {
        // Ctrl+K o Cmd+K
        if ((e.ctrlKey || e.metaKey) && (e.key === 'k' || e.key === 'K')) {
          e.preventDefault();
          OmniSearch.toggle();
        }
        // Tecla "/" si no estamos escribiendo en otro input
        if (e.key === '/' && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName)) {
          e.preventDefault();
          OmniSearch.open();
        }
      });

      // Actualizar conteos
      const countEl = document.getElementById('omni-count-all');
      if (countEl) countEl.textContent = OmniSearchState.patientsCache.length || 25;

      // Mejorar selects nativos
      _upgradeNativeSelectToCombobox('exp-patient-select');
      _upgradeNativeSelectToCombobox('dashboard-patient-select');
      _upgradeNativeSelectToCombobox('consulta-patient-dropdown');
      _upgradeNativeSelectToCombobox('lab-patient-select');
      _upgradeNativeSelectToCombobox('ask-patient-select');

      console.log('✅ OmniSearch Premium Engine v3.0 listo para miles de pacientes.');
    },

    open(initialQuery = '') {
      const modal = document.getElementById('omni-search-modal');
      const input = document.getElementById('omni-search-input');
      if (!modal) return;

      modal.style.display = 'flex';
      OmniSearchState.isOpen = true;
      OmniSearchState.query = initialQuery;
      OmniSearchState.selectedIndex = 0;

      if (input) {
        input.value = initialQuery;
        setTimeout(() => input.focus(), 50);
      }

      _executeSearch();
    },

    close() {
      const modal = document.getElementById('omni-search-modal');
      if (!modal) return;
      modal.style.display = 'none';
      OmniSearchState.isOpen = false;
    },

    toggle() {
      if (OmniSearchState.isOpen) this.close();
      else this.open();
    },

    clearInput() {
      const input = document.getElementById('omni-search-input');
      if (input) {
        input.value = '';
        input.focus();
      }
      this.onInputChange('');
    },

    setCategory(cat) {
      OmniSearchState.filterCategory = cat;
      const chips = document.querySelectorAll('.omni-filter-chip');
      chips.forEach(c => {
        c.classList.toggle('active', c.getAttribute('data-cat') === cat);
      });
      _executeSearch();
    },

    setSelectedIndex(idx) {
      OmniSearchState.selectedIndex = idx;
      const items = document.querySelectorAll('.omni-result-item');
      items.forEach((el, i) => {
        el.classList.toggle('is-selected', i === idx);
      });
    },

    onInputChange(val) {
      OmniSearchState.query = val;
      _executeSearch();
    },

    onKeyDown(e) {
      const results = OmniSearchState.results;
      if (!results || results.length === 0) {
        if (e.key === 'Escape') this.close();
        return;
      }

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        OmniSearchState.selectedIndex = (OmniSearchState.selectedIndex + 1) % results.length;
        this.setSelectedIndex(OmniSearchState.selectedIndex);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        OmniSearchState.selectedIndex = (OmniSearchState.selectedIndex - 1 + results.length) % results.length;
        this.setSelectedIndex(OmniSearchState.selectedIndex);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const activeItem = results[OmniSearchState.selectedIndex];
        if (activeItem) {
          const curp = activeItem.curp || activeItem.patient_curp;
          const targetTab = e.ctrlKey ? 'consulta' : 'expediente';
          this.selectPatient(curp, targetTab);
        }
      } else if (e.key === 'Escape') {
        this.close();
      }
    },

    // Selección de paciente y sincronización completa
    async selectPatient(curp, targetView = 'expediente') {
      if (!curp) return;
      this.close();

      const upperCurp = String(curp).trim().toUpperCase();
      console.log(`[OmniSearch] Paciente seleccionado: ${upperCurp} -> Vista: ${targetView}`);

      // Asegurar caché de pacientes
      await _ensurePatientsCache();
      const patient = OmniSearchState.patientsCache.find(p => (p.curp || '').toUpperCase() === upperCurp);

      // Sincronizar estado global
      if (window.AppState) {
        window.AppState.selectedPatientCurp = upperCurp;
        window.AppState.activeCurp = upperCurp;
      }
      if (typeof window._ExpCareState !== 'undefined') {
        window._ExpCareState.curp = upperCurp;
      }

      // Actualizar selects nativos y comboboxes en toda la app
      ['exp-patient-select', 'dashboard-patient-select', 'consulta-patient-dropdown', 'lab-patient-select'].forEach(selId => {
        const sel = document.getElementById(selId);
        if (sel) {
          sel.value = upperCurp;
          if (patient) _updateComboboxTrigger(selId, patient);
        }
      });

      // Redirigir a la vista solicitada y sincronizar carga de expediente
      try {
        if (targetView === 'dashboard') {
          if (typeof window.switchMainTab === 'function') window.switchMainTab('dashboard');
          if (typeof window.onDashboardPatientChange === 'function') await window.onDashboardPatientChange(upperCurp);
        } else if (targetView === 'consulta') {
          if (typeof window.switchMainTab === 'function') window.switchMainTab('consulta');
          if (typeof window.onConsultaPatientSelect === 'function') window.onConsultaPatientSelect(upperCurp);
        } else if (targetView === 'lab') {
          if (typeof window.openLaboratorioModal === 'function') window.openLaboratorioModal();
          if (typeof window.onLabPatientChange === 'function') window.onLabPatientChange(upperCurp);
        } else {
          if (typeof window.switchMainTab === 'function') window.switchMainTab('expediente');
          if (typeof window.loadSpecializedPatient === 'function') {
            await window.loadSpecializedPatient(upperCurp);
          }
        }
      } catch (err) {
        console.error('[OmniSearch] Error cargando paciente en vista ' + targetView + ':', err);
      }

      if (typeof window.showToast === 'function') {
        const pName = patient ? `${patient.nombres || ''} ${patient.primer_apellido || ''}`.trim() : upperCurp;
        window.showToast(`Expediente cargado: ${pName}`, 'info');
      }
    },

    // Métodos del combobox
    toggleCombobox(selectId) {
      const dd = document.getElementById(`${selectId}-dropdown`);
      const btn = document.getElementById(`${selectId}-btn`);
      const input = document.getElementById(`${selectId}-filter-input`);
      if (!dd) return;

      const isOpen = dd.style.display !== 'none';
      dd.style.display = isOpen ? 'none' : 'block';
      if (btn) btn.setAttribute('aria-expanded', isOpen ? 'false' : 'true');

      if (!isOpen && input) {
        input.value = '';
        this.filterCombobox(selectId, '');
        setTimeout(() => input.focus(), 50);
      }
    },

    filterCombobox(selectId, text) {
      const container = document.getElementById(`${selectId}-items-container`);
      if (!container) return;

      const clean = (text || '').trim().toLowerCase();
      const items = container.querySelectorAll('.combobox-item');

      items.forEach(it => {
        const searchable = it.getAttribute('data-text') || '';
        if (!clean || searchable.includes(clean)) {
          it.style.display = 'flex';
        } else {
          it.style.display = 'none';
        }
      });
    },

    async chooseComboboxOption(selectId, curp) {
      if (!curp) return;
      const upperCurp = String(curp).trim().toUpperCase();

      const dd = document.getElementById(`${selectId}-dropdown`);
      const btn = document.getElementById(`${selectId}-btn`);
      if (dd) dd.style.display = 'none';
      if (btn) btn.setAttribute('aria-expanded', 'false');

      await _ensurePatientsCache();
      const patient = OmniSearchState.patientsCache.find(p => (p.curp || '').toUpperCase() === upperCurp);

      // Sincronizar estado global
      if (window.AppState) {
        window.AppState.selectedPatientCurp = upperCurp;
        window.AppState.activeCurp = upperCurp;
      }
      if (typeof window._ExpCareState !== 'undefined') {
        window._ExpCareState.curp = upperCurp;
      }

      // Sincronizar todos los comboboxes y selects nativos
      ['exp-patient-select', 'dashboard-patient-select', 'consulta-patient-dropdown', 'lab-patient-select', 'ask-patient-select'].forEach(id => {
        const el = document.getElementById(id);
        if (el) {
          el.value = upperCurp;
          el.dispatchEvent(new Event('change', { bubbles: true }));
        }
        if (patient) _updateComboboxTrigger(id, patient);
      });

      // Cargar vista correspondiente
      try {
        if (selectId === 'exp-patient-select' && typeof window.loadSpecializedPatient === 'function') {
          await window.loadSpecializedPatient(upperCurp);
        } else if (selectId === 'dashboard-patient-select' && typeof window.onDashboardPatientChange === 'function') {
          await window.onDashboardPatientChange(upperCurp);
        } else if (selectId === 'consulta-patient-dropdown' && typeof window.onConsultaPatientSelect === 'function') {
          window.onConsultaPatientSelect(upperCurp);
        } else if (selectId === 'lab-patient-select' && typeof window.onLabPatientChange === 'function') {
          window.onLabPatientChange(upperCurp);
        } else if (selectId === 'ask-patient-select') {
          const askBox = document.getElementById('ask-response-box');
          if (askBox) askBox.textContent = 'Paciente seleccionado. Escribe una pregunta o pulsa un botón rápido arriba para consultar su historial.';
        }
      } catch (err) {
        console.error('[OmniSearch] Error en chooseComboboxOption:', err);
      }

      if (typeof window.showToast === 'function') {
        const pName = patient ? `${patient.nombres || ''} ${patient.primer_apellido || ''}`.trim() : upperCurp;
        window.showToast(`Paciente seleccionado: ${pName}`, 'info');
      }
    },

    upgradeSelect(selectId, onSelectCallback) {
      _upgradeNativeSelectToCombobox(selectId, onSelectCallback);
    },

    syncAllTriggers(curp) {
      if (!curp) return;
      const upperCurp = String(curp).trim().toUpperCase();
      const patient = OmniSearchState.patientsCache.find(p => (p.curp || '').toUpperCase() === upperCurp);
      ['exp-patient-select', 'dashboard-patient-select', 'consulta-patient-dropdown', 'lab-patient-select', 'ask-patient-select'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = upperCurp;
        if (patient) _updateComboboxTrigger(id, patient);
      });
    },

    // Refrescar datos en todos los componentes
    refreshAll() {
      OmniSearchState.patientsCache = [];
      _ensurePatientsCache().then(() => {
        ['exp-patient-select', 'dashboard-patient-select', 'consulta-patient-dropdown', 'lab-patient-select', 'ask-patient-select'].forEach(id => {
          _refreshComboboxData(id);
        });
      });
    }
  };

  // Inicializar automáticamente cuando el DOM esté listo
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => window.OmniSearch.init());
  } else {
    window.OmniSearch.init();
  }

})();
