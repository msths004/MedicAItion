"""
update_frontend_interhospital.py — Inyección de la UI de Red Interhospitalaria Federada
"""

import os

HTML_PATH = os.path.abspath("frontend/index.html")
JS_PATH = os.path.abspath("frontend/app.js")
CSS_PATH = os.path.abspath("frontend/style.css")

LINUX_HTML = os.path.abspath("Linux_Ver/frontend/index.html")
LINUX_JS = os.path.abspath("Linux_Ver/frontend/app.js")
LINUX_CSS = os.path.abspath("Linux_Ver/frontend/style.css")

SIDEBAR_BTN_HTML = """
        <button class="sidebar-nav-btn" id="nav-btn-red-hospitalaria" onclick="switchMainTab('red-hospitalaria')" title="Red Interhospitalaria Federada, Interconsulta y Referencias NOM-004">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/></svg>
          <span>Red Hospitalaria</span>
          <span class="nav-badge-blue" id="red-hosp-badge" style="background:#e0f2fe; color:#0284c7; font-size:10px; font-weight:700; padding:2px 6px; border-radius:10px; margin-left:auto;">7 Nodos</span>
        </button>"""

TOPBAR_PILL_HTML = """
          <!-- Red Hospitalaria Node Badge -->
          <div class="hospital-network-pill" onclick="switchMainTab('red-hospitalaria')" title="Red Interhospitalaria Federada: Sede Activa Cruz Roja Mérida (YUC-CR-001) - 7 Hospitales Conectados">
            <span class="hosp-net-icon">🏥</span>
            <div class="hosp-net-info">
              <span class="hosp-net-title">Cruz Roja Mérida (YUC-CR-001)</span>
              <span class="hosp-net-sub">Red Yucatán Conectada (7 Nodos)</span>
            </div>
            <span class="hosp-net-dot"></span>
          </div>"""

RED_HOSPITALARIA_PANEL_HTML = """
        <!-- =================================================================
             VIEW: RED INTERHOSPITALARIA & INTERCONSULTA FEDERADA (NOM-024 / FHIR)
             ================================================================= -->
        <section class="view-panel" id="panel-red-hospitalaria-section" style="display:none">
          <div class="red-hospital-container">
            <!-- Header -->
            <div class="red-header">
              <div class="red-header-text">
                <div class="red-title-tag">
                  <span class="red-tag-badge">INTEROPERABILIDAD NOM-024-SSA3-2012</span>
                  <span class="red-tag-badge-accent">HL7 FHIR R4 FEDERADO</span>
                </div>
                <h1>Red Hospitalaria & Interconsulta Federada</h1>
                <p>Intercomunicación clínica segura entre hospitales de Yucatán. Acceso ultrarrápido en urgencias con salvaguarda <strong>Safe Harbor</strong> y soberanía de datos locales (Cero almacenamiento centralizado de notas).</p>
              </div>
              <div class="red-header-actions">
                <button type="button" class="btn-outline-pill" onclick="initRedHospitalariaView()" title="Actualizar estado de nodos y latencia">↻ Sincronizar Red</button>
                <button type="button" class="btn-dark-pill" onclick="openNewReferralFormModal()" title="Emitir orden de traslado a otro hospital">➕ Emitir Referencia NOM-004</button>
              </div>
            </div>

            <!-- Bento KPIs Grid -->
            <div class="red-kpi-grid">
              <div class="bento-card red-kpi-card">
                <div class="bento-label">HOSPITALES CONECTADOS</div>
                <div class="bento-value" id="kpi-net-nodes">7 Nodos</div>
                <div class="bento-desc">Red Peninsular Yucatán (SSY • IMSS • Cruz Roja • ISSSTE)</div>
              </div>
              <div class="bento-card red-kpi-card">
                <div class="bento-label">LATENCIA PROMEDIO RED</div>
                <div class="bento-value text-accent" id="kpi-net-latency">12.4 ms</div>
                <div class="bento-desc">Enlace seguro de alta velocidad para urgencias</div>
              </div>
              <div class="bento-card red-kpi-card">
                <div class="bento-label">PROTECCIÓN & PRIVACIDAD</div>
                <div class="bento-value text-success" id="kpi-net-security">Zero-Knowledge</div>
                <div class="bento-desc">Sin almacén central de notas • ChaCha20 + HMAC-SHA256</div>
              </div>
              <div class="bento-card red-kpi-card">
                <div class="bento-label">REFERENCIAS NOM-004</div>
                <div class="bento-value text-amber" id="kpi-net-referrals">3 Activas</div>
                <div class="bento-desc">1 en tránsito de ambulancia • 2 aceptadas</div>
              </div>
            </div>

            <!-- BUSCADOR INTERHOSPITALARIO DE PACIENTES -->
            <div class="bento-card red-search-card">
              <div class="bento-card-header">
                <div>
                  <h3 style="margin:0; font-size:16px; color:#0f172a; display:flex; align-items:center; gap:8px;">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0284c7" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
                    Buscador de Red Interhospitalaria (Búsqueda Federada)
                  </h3>
                  <p style="margin:3px 0 0 0; font-size:13px; color:#64748b;">Localiza antecedentes y resguardos vitales del paciente en cualquier hospital conectado usando su CURP o Nombre.</p>
                </div>
                <!-- Mode Switcher -->
                <div class="access-mode-toggle" role="group" aria-label="Nivel de Acceso y Privacidad">
                  <button type="button" class="mode-toggle-btn active" id="btn-mode-urgencias" onclick="setNetworkSearchMode('urgencias_rojo')" title="Desbloqueo inmediato de alergias y sangre para emergencias vitales">
                    🚨 Urgencias (Código Rojo)
                  </button>
                  <button type="button" class="mode-toggle-btn" id="btn-mode-interconsulta" onclick="setNetworkSearchMode('interconsulta_consentida')" title="Consulta de especialidad con consentimiento informado">
                    📋 Interconsulta Formal (NOM-024)
                  </button>
                </div>
              </div>

              <!-- Search Bar & Controls -->
              <div class="red-search-controls">
                <div class="red-search-input-wrap">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#64748b" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
                  <input type="text" id="network-search-input" placeholder="Ingresa CURP o Nombre completo del paciente (ej. MOBK070228..., Teresa Alvarado)..." onkeydown="if(event.key==='Enter') executeNetworkSearch();" />
                  <button type="button" class="btn-dark-pill" onclick="executeNetworkSearch()">Buscar en Red</button>
                </div>
                <div class="red-quick-pills">
                  <span style="font-size:12px; color:#64748b; font-weight:600;">Casos de demostración:</span>
                  <button type="button" class="quick-curp-pill" onclick="quickFillNetworkSearch('Kevin Enrique Morales')">Kevin Morales (Politrauma / O'Horán)</button>
                  <button type="button" class="quick-curp-pill" onclick="quickFillNetworkSearch('Teresa Alvarado')">Teresa Alvarado (Diabetes / IMSS T-1)</button>
                  <button type="button" class="quick-curp-pill" onclick="quickFillNetworkSearch('Rosaura Macías')">Rosaura Macías (Dengue Alarma)</button>
                  <button type="button" class="quick-curp-pill" onclick="quickFillNetworkSearch('Diego Canto')">Diego Canto (Asma / Kanasín)</button>
                </div>
              </div>

              <!-- Privacy Notice Banner inside search -->
              <div class="safe-harbor-info-banner" id="search-mode-banner">
                <div class="sh-icon">🛡️</div>
                <div class="sh-text">
                  <strong id="sh-title">MODO URGENCIAS / CÓDIGO ROJO SELECCIONADO (Safe Harbor NOM-024)</strong>
                  <span id="sh-desc">Acceso instantáneo (&lt;1s) al Núcleo de Salvaguarda Vital: Tipo de sangre, Alergias mortales y Medicamentos de riesgo. Las notas íntimas y consultas de salud mental están estrictamente bloqueadas. Se estampará un sello de auditoría HMAC con su Cédula Profesional (CED-9482710).</span>
                </div>
              </div>

              <!-- Results Box -->
              <div id="network-search-results-area" style="display:none; margin-top:20px;">
                <!-- Populated dynamically via JS -->
              </div>
            </div>

            <!-- DOS COLUMNAS: REFERENCIAS ACTIVAS + TOPOLOGÍA DE HOSPITALES -->
            <div class="red-two-col">
              <!-- COLUMNA IZQUIERDA: GESTIÓN DE REFERENCIA Y CONTRARREFERENCIA (NOM-004) -->
              <div class="bento-card">
                <div class="bento-card-header" style="border-bottom:1px solid #f1f5f9; padding-bottom:12px; margin-bottom:16px;">
                  <div>
                    <h3 style="margin:0; font-size:15px; color:#0f172a; display:flex; align-items:center; gap:8px;">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0284c7" stroke-width="2"><path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/></svg>
                      Referencias y Traslados Interhospitalarios (NOM-004-SSA3-2012)
                    </h3>
                    <p style="margin:2px 0 0 0; font-size:12.5px; color:#64748b;">Órdenes activas de traslado y recepción de pacientes entre instituciones del estado.</p>
                  </div>
                </div>

                <div class="referrals-table-wrap">
                  <table class="red-data-table" id="table-referrals">
                    <thead>
                      <tr>
                        <th>Folio</th>
                        <th>Paciente / CURP</th>
                        <th>Origen ➔ Destino</th>
                        <th>Motivo / Diagnóstico</th>
                        <th>Prioridad</th>
                        <th>Estado</th>
                        <th>Acción</th>
                      </tr>
                    </thead>
                    <tbody id="referrals-tbody">
                      <!-- Filled via JS -->
                    </tbody>
                  </table>
                </div>
              </div>

              <!-- COLUMNA DERECHA: DIRECTORIO Y TOPOLOGÍA DE NODOS HOSPITALARIOS -->
              <div class="bento-card">
                <div class="bento-card-header" style="border-bottom:1px solid #f1f5f9; padding-bottom:12px; margin-bottom:16px;">
                  <div>
                    <h3 style="margin:0; font-size:15px; color:#0f172a; display:flex; align-items:center; gap:8px;">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0284c7" stroke-width="2"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="m9 9 6 6m0-6-6 6"/></svg>
                      Nodos Federados en Yucatán (Directorio CLUES)
                    </h3>
                    <p style="margin:2px 0 0 0; font-size:12.5px; color:#64748b;">Centros médicos interconectados con protocolo de interoperabilidad.</p>
                  </div>
                </div>

                <div class="hospital-nodes-grid" id="hospital-nodes-list">
                  <!-- Filled via JS -->
                </div>
              </div>
            </div>

            <!-- BITÁCORA INMUTABLE DE AUDITORÍA NOM-024 / LFPDPPP -->
            <div class="bento-card" style="margin-top:20px;">
              <div class="bento-card-header" style="border-bottom:1px solid #f1f5f9; padding-bottom:12px; margin-bottom:16px;">
                <div>
                  <h3 style="margin:0; font-size:15px; color:#0f172a; display:flex; align-items:center; gap:8px;">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0284c7" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10"/><path d="m9 12 2 2 4-4"/></svg>
                    Auditoría Interhospitalaria Inmutable (Trazabilidad NOM-024)
                  </h3>
                  <p style="margin:2px 0 0 0; font-size:12.5px; color:#64748b;">Cada consulta interhospitalaria queda sellada con HMAC-SHA256 y la Cédula Profesional del médico.</p>
                </div>
              </div>

              <div class="referrals-table-wrap">
                <table class="red-data-table" id="table-audits">
                  <thead>
                    <tr>
                      <th>Fecha / Hora</th>
                      <th>Médico Requirente</th>
                      <th>Hospital Solicitante</th>
                      <th>Paciente (CURP)</th>
                      <th>Nivel de Acceso</th>
                      <th>Justificación Clínica</th>
                      <th>Sello HMAC-SHA256</th>
                    </tr>
                  </thead>
                  <tbody id="audits-tbody">
                    <!-- Filled via JS -->
                  </tbody>
                </table>
              </div>
            </div>

          </div>
        </section>

        <!-- MODAL: EMITIR NUEVA REFERENCIA INTERHOSPITALARIA -->
        <div id="modal-new-referral" class="modal-overlay" style="display:none;" onclick="if(event.target===this) closeNewReferralModal();">
          <div class="modal-dialog-large" style="max-width:680px; background:#fff; border-radius:16px; padding:24px; box-shadow:0 20px 40px rgba(0,0,0,0.18);">
            <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #e2e8f0; padding-bottom:12px; margin-bottom:16px;">
              <div>
                <h3 style="margin:0; font-size:17px; color:#0f172a;">Emitir Orden de Referencia Interhospitalaria (NOM-004)</h3>
                <span style="font-size:12.5px; color:#64748b;">Hospital Emisor: <strong>Cruz Roja Mexicana Delegación Mérida (YUC-CR-001)</strong></span>
              </div>
              <button type="button" class="btn-icon" onclick="closeNewReferralModal()" style="font-size:20px; border:none; background:none; cursor:pointer;">✕</button>
            </div>

            <form onsubmit="submitNewReferralForm(event)">
              <div style="display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:12px;">
                <div>
                  <label style="font-size:12px; font-weight:700; color:#334155; display:block; margin-bottom:4px;">CURP DEL PACIENTE *</label>
                  <input type="text" id="ref-pat-curp" required placeholder="ej. MOBK070228HYNRTVA3" style="width:100%; padding:8px 12px; border:1px solid #cbd5e1; border-radius:8px; font-size:13px;" />
                </div>
                <div>
                  <label style="font-size:12px; font-weight:700; color:#334155; display:block; margin-bottom:4px;">NOMBRE COMPLETO DEL PACIENTE *</label>
                  <input type="text" id="ref-pat-name" required placeholder="ej. Kevin Enrique Morales Bautista" style="width:100%; padding:8px 12px; border:1px solid #cbd5e1; border-radius:8px; font-size:13px;" />
                </div>
              </div>

              <div style="display:grid; grid-template-columns:1fr 1fr; gap:14px; margin-bottom:12px;">
                <div>
                  <label style="font-size:12px; font-weight:700; color:#334155; display:block; margin-bottom:4px;">HOSPITAL RECEPTOR DE DESTINO *</label>
                  <select id="ref-hospital-destino" required style="width:100%; padding:8px 12px; border:1px solid #cbd5e1; border-radius:8px; font-size:13px;">
                    <option value="YCSSA000024|Hospital General Dr. Agustín O'Horán">Hospital General Dr. Agustín O'Horán (Trauma & 3er Nivel)</option>
                    <option value="IMS0001092|HGR N° 1 T-1 Lic. Ignacio García Téllez">HGR N° 1 T-1 Lic. Ignacio García Téllez (IMSS)</option>
                    <option value="YCSSA000671|Hospital Materno-Infantil de Mérida">Hospital Materno-Infantil de Mérida</option>
                    <option value="YUC-HRA-003|Hospital Regional de Alta Especialidad (HRAEPY)">Hospital Regional de Alta Especialidad (HRAEPY)</option>
                    <option value="ISS0003412|Hospital Regional Mérida ISSSTE">Hospital Regional Mérida ISSSTE</option>
                    <option value="YCSSA001890|Centro de Salud Urbano Kanasín">Centro de Salud Urbano Kanasín</option>
                  </select>
                </div>
                <div>
                  <label style="font-size:12px; font-weight:700; color:#334155; display:block; margin-bottom:4px;">PRIORIDAD DEL TRASLADO *</label>
                  <select id="ref-prioridad" style="width:100%; padding:8px 12px; border:1px solid #cbd5e1; border-radius:8px; font-size:13px;">
                    <option value="Urgencia">🚨 Urgencia Inmediata (Código Rojo)</option>
                    <option value="Prioritaria">⚠️ Prioritaria (&lt; 24 Horas)</option>
                    <option value="Ordinaria">📅 Ordinaria / Programada</option>
                  </select>
                </div>
              </div>

              <div style="margin-bottom:12px;">
                <label style="font-size:12px; font-weight:700; color:#334155; display:block; margin-bottom:4px;">DIAGNÓSTICO PRESUNTIVO / CIE-10 *</label>
                <input type="text" id="ref-cie10" required placeholder="ej. S06.0 Conmoción cerebral o TCE leve" style="width:100%; padding:8px 12px; border:1px solid #cbd5e1; border-radius:8px; font-size:13px;" />
              </div>

              <div style="margin-bottom:12px;">
                <label style="font-size:12px; font-weight:700; color:#334155; display:block; margin-bottom:4px;">MOTIVO DE ENVÍO / JUSTIFICACIÓN CLÍNICA *</label>
                <textarea id="ref-motivo" required rows="2" placeholder="Describa por qué el paciente requiere atención en el hospital receptor..." style="width:100%; padding:8px 12px; border:1px solid #cbd5e1; border-radius:8px; font-size:13px;"></textarea>
              </div>

              <div style="margin-bottom:18px;">
                <label style="font-size:12px; font-weight:700; color:#334155; display:block; margin-bottom:4px;">RESUMEN CLÍNICO, SIGNOS VITALES Y ALERGIAS (NOM-004)</label>
                <textarea id="ref-detalles" rows="3" placeholder="TA, FC, SpO2, estado de consciencia, alergias documentadas..." style="width:100%; padding:8px 12px; border:1px solid #cbd5e1; border-radius:8px; font-size:13px;"></textarea>
              </div>

              <div style="display:flex; justify-content:flex-end; gap:10px;">
                <button type="button" class="btn-outline-pill" onclick="closeNewReferralModal()">Cancelar</button>
                <button type="submit" class="btn-dark-pill" style="background:#0284c7; border-color:#0284c7;">✓ Emitir y Transmitir a Hospital Receptor</button>
              </div>
            </form>
          </div>
        </div>
"""

def update_file(path, search_str, insert_str, before=False):
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if insert_str.strip() in content:
        print(f"Already injected in {os.path.basename(path)}")
        return True
    if search_str not in content:
        print(f"Anchor '{search_str[:30]}...' not found in {os.path.basename(path)}")
        return False
    if before:
        new_content = content.replace(search_str, insert_str + "\n" + search_str, 1)
    else:
        new_content = content.replace(search_str, search_str + "\n" + insert_str, 1)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Successfully updated {os.path.basename(path)}")
    return True

print("Modificando frontend/index.html...")
# 1. Sidebar Nav
with open(HTML_PATH, "r", encoding="utf-8") as f:
    h = f.read()

if "nav-btn-red-hospitalaria" not in h:
    target = 'id="nav-btn-ia-tools"'
    # Find end of this button
    idx = h.find(target)
    if idx != -1:
        end_btn = h.find("</button>", idx) + len("</button>")
        h = h[:end_btn] + "\n" + SIDEBAR_BTN_HTML + h[end_btn:]
        print("Sidebar button injected.")

# 2. Topbar Pill
if "hospital-network-pill" not in h:
    target_top = '<div class="status-sync-wrap" id="status-badge">'
    idx_top = h.find(target_top)
    if idx_top != -1:
        # Find closing tag of status-badge
        end_top = h.find("</div>", idx_top)
        # find the outer div close
        end_top_outer = h.find("</div>", end_top + 6) + len("</div>")
        h = h[:end_top_outer] + "\n" + TOPBAR_PILL_HTML + h[end_top_outer:]
        print("Topbar pill injected.")

# 3. View Panel
if "panel-red-hospitalaria-section" not in h:
    target_panel = '<section class="view-panel" id="panel-reports-section"'
    idx_p = h.find(target_panel)
    if idx_p != -1:
        h = h[:idx_p] + RED_HOSPITALARIA_PANEL_HTML + "\n" + h[idx_p:]
        print("Panel red-hospitalaria injected.")

with open(HTML_PATH, "w", encoding="utf-8") as f:
    f.write(h)

# Sincronizar a Linux_Ver
if os.path.exists(LINUX_HTML):
    with open(LINUX_HTML, "w", encoding="utf-8") as f:
        f.write(h)
    print("Sincronizado a Linux_Ver/frontend/index.html")

print("Listo index.html.")
