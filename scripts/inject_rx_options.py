# -*- coding: utf-8 -*-
import os
BASE = r"C:\Users\Kevin\.gemini\antigravity\scratch\MedicAItion"
idx_path = os.path.join(BASE, "frontend", "index.html")
linux_idx_path = os.path.join(BASE, "Linux_Ver", "frontend", "index.html")

with open(idx_path, 'r', encoding='utf-8') as f:
    c = f.read()

btn_target = """                <button class="segmented-btn" id="btn-text" onclick="setMode('text')">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>
                  <span>Texto</span>
                </button>"""

btn_replacement = btn_target + """
                <button class="segmented-btn" id="btn-transcripcion" onclick="setMode('transcripcion')" title="Transcribir foto de receta médica manuscrita 100% en local">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"/><circle cx="12" cy="13" r="3"/></svg>
                  <span>Transcripción</span>
                </button>"""

rx_panel_target = """            <!-- TEXT CAPTURE CARD -->
            <div id="text-panel" class="input-panel" style="display:none">
              <div class="textarea-card">
                <textarea id="text-input" class="textarea-field" rows="7"
                  placeholder="Describe el caso clínico: síntomas, signos vitales, antecedentes, diagnósticos presuntivos, medicamentos con dosis y plan de seguimiento..."></textarea>
                <div class="textarea-footer">
                  <span class="textarea-hint">El extractor inteligente identificará signos vitales, CIE-10 y receta automáticamente</span>
                </div>
              </div>
            </div>"""

rx_panel = """

            <!-- PRESCRIPTION IMAGE TRANSCRIPTION CARD (100% LOCAL OCR + VISION) -->
            <div id="transcripcion-panel" class="input-panel" style="display:none">
              <div class="rx-ocr-card">
                <div class="rx-ocr-header">
                  <div class="rx-ocr-badge">
                    <span class="rx-ocr-dot"></span>
                    <span id="rx-ocr-engine-label">🔒 IA Visión Médica 100% Local (TrOCR Handwritten + RapidOCR ONNX + Farmacopea)</span>
                  </div>
                  <span class="rx-ocr-zero-cloud">Zero-Cloud · Cero Fuga de Datos</span>
                </div>

                <div class="rx-samples-bar">
                  <span class="rx-samples-label">Probar con receta manuscrita:</span>
                  <button type="button" class="rx-sample-chip" onclick="runRxSampleTranscription('respiratoria')">
                    📝 Receta #1: Infección Resp.
                  </button>
                  <button type="button" class="rx-sample-chip" onclick="runRxSampleTranscription('cardiometabolica')">
                    📝 Receta #2: Control DM2 / HAS
                  </button>
                  <button type="button" class="rx-sample-chip" onclick="runRxSampleTranscription('gastro')">
                    📝 Receta #3: Gastritis / Dolor
                  </button>
                </div>

                <div class="rx-dropzone" id="rx-dropzone" onclick="document.getElementById('rx-file-input').click()">
                  <input type="file" id="rx-file-input" accept="image/*" style="display:none" onchange="handleRxFileSelect(event)" />
                  <div id="rx-dropzone-empty" class="rx-dropzone-empty">
                    <div class="rx-dropzone-icon">
                      <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z"/><circle cx="12" cy="13" r="3"/></svg>
                    </div>
                    <div class="rx-dropzone-title">Arrastra aquí la foto de la receta médica o haz clic para subirla</div>
                    <div class="rx-dropzone-sub">Optimizado para caligrafía médica ('letra de doctor') · Formatos JPG, PNG, WEBP · Procesamiento 100% en tu equipo</div>
                  </div>
                  <div id="rx-preview-container" class="rx-preview-container" style="display:none">
                    <img id="rx-image-preview" class="rx-image-preview" alt="Vista previa de receta médica" />
                    <div class="rx-preview-actions">
                      <span id="rx-preview-filename" class="rx-preview-filename">receta.png</span>
                      <button type="button" class="rx-btn-change-img" onclick="event.stopPropagation(); document.getElementById('rx-file-input').click();">
                        🔄 Cambiar imagen
                      </button>
                    </div>
                  </div>
                </div>

                <div id="rx-ocr-loading" class="rx-ocr-loading" style="display:none">
                  <div class="rx-ocr-spinner"></div>
                  <div class="rx-ocr-loading-text">
                    <strong>Descifrando caligrafía médica en hardware local...</strong>
                    <span>Ejecutando realce CLAHE + RapidOCR ONNX + TrOCR Handwritten + Validación Farmacológica</span>
                  </div>
                </div>

                <div id="rx-structured-results" class="rx-structured-results" style="display:none">
                  <div class="rx-results-header">
                    <div>
                      <h4 class="rx-results-title">📋 Receta Digitalizada y Estructurada (Editable)</h4>
                      <span id="rx-results-meta" class="rx-results-meta">Verifique o edite cualquier campo antes de integrar a la consulta</span>
                    </div>
                    <div class="rx-results-header-btns">
                      <button type="button" class="rx-btn-add-med" onclick="addRxMedicationRow()">+ Agregar fármaco</button>
                      <button type="button" class="rx-btn-sync-text" onclick="syncRxToClinicalText(true)" title="Copiar la receta estructurada al editor de texto clínico">
                        📋 Pasar a Texto
                      </button>
                    </div>
                  </div>
                  <div id="rx-detected-header-info" class="rx-detected-header-info" style="display:none"></div>
                  <div id="rx-safety-banner" class="rx-safety-banner" style="display:none"></div>
                  <div id="rx-medications-list" class="rx-medications-list"></div>
                </div>
              </div>
            </div>"""

if btn_target in c:
    c = c.replace(btn_target, btn_replacement, 1)
    print("Inserted btn-transcripcion")
else:
    print("btn_target not found")

if rx_panel_target in c:
    c = c.replace(rx_panel_target, rx_panel_target + rx_panel, 1)
    print("Inserted rx_panel")
else:
    print("rx_panel_target not found")

with open(idx_path, 'w', encoding='utf-8') as f:
    f.write(c)

with open(linux_idx_path, 'w', encoding='utf-8') as f:
    f.write(c)

print("Updated index.html and Linux_Ver successfully.")
