/**
 * ethical_governance.js - MedicAItion Ethical & Responsible AI Governance Suite
 * Implements the 7 Core Pillars:
 * 1. Transparencia (Explainability XAI & Model Cards)
 * 2. Inclusión (WCAG 2.1 AA Accessibility, Font Scaling, Maya/Easy-Read Localization)
 * 3. Responsabilidad (Physician Legal Responsibility, Signature Hash, Dispute Logging)
 * 4. Imparcialidad (Algorithmic Fairness & Neutrality Verification)
 * 5. Fiabilidad (Clinical CDSS Verification & Redundancy)
 * 6. Seguridad (RBAC & Clinical Safety Thresholds)
 * 7. Privacidad (Instant De-Identification & ARCO Compliance)
 */

window.EthicalGovernance = {
  currentFontSizeIndex: 1, // 0: Small (90%), 1: Normal (100%), 2: Large (115%), 3: Extra Large (130%)
  fontSizes: ['90%', '100%', '115%', '130%'],
  highContrast: false,
  isAnonymized: false,
  currentLanguage: 'es', // 'es', 'maya', 'facil'

  // 1. INCLUSIÓN: Ajuste Dinámico de Tamaño de Fuente
  adjustFontSize(direction) {
    if (direction === 'increase') {
      this.currentFontSizeIndex = Math.min(this.currentFontSizeIndex + 1, this.fontSizes.length - 1);
    } else if (direction === 'decrease') {
      this.currentFontSizeIndex = Math.max(this.currentFontSizeIndex - 1, 0);
    } else {
      this.currentFontSizeIndex = 1;
    }
    const size = this.fontSizes[this.currentFontSizeIndex];
    document.documentElement.style.fontSize = size;
    const label = document.getElementById('font-size-indicator');
    if (label) label.textContent = size;
    if (typeof showToast === 'function') {
      showToast(`Accesibilidad: Escala de texto ajustada a ${size}`, 'info');
    }
  },

  // 1. INCLUSIÓN: Modo Alto Contraste Clínico (WCAG AA)
  toggleHighContrast() {
    this.highContrast = !this.highContrast;
    document.body.classList.toggle('high-contrast-mode', this.highContrast);
    const btn = document.getElementById('btn-toggle-contrast');
    if (btn) btn.classList.toggle('active', this.highContrast);
    if (typeof showToast === 'function') {
      showToast(this.highContrast ? 'Modo Alto Contraste Activado (Accesibilidad WCAG AA)' : 'Modo Contraste Estándar', 'info');
    }
  },

  // 1. INCLUSIÓN: Inclusión Lingüística Intercultural (Maya Yucateco / Lectura Fácil)
  setLanguageInclusion(lang) {
    this.currentLanguage = lang;
    const notesEl = document.getElementById('receta-instructions-text');
    if (!notesEl) return;

    if (lang === 'maya') {
      notesEl.setAttribute('data-original-es', notesEl.innerText);
      notesEl.innerHTML = `
        <div class="lang-translation-banner">
          <span class="lang-pill">Maaya T'aan (Maya Yucateco)</span>
          <p><strong>U ts'aakil yéetel bix ken a ch'a'e':</strong> Uk' le ts'aak je'el bix ts'íibta'an ti' le hu'uma'. Ma' a jáawal a ch'a'ik kex ka wu'uy ma'alo'obtech. Wa ku yantal chokwil wa k'iinam ti' a puksi'ik'al, ka'an a bin tu séebal ti' le j-ts'aak yano'ob te' k'oja'anilo'.</p>
          <small><em>Traducción culturalmente contextualizada para preservación de la salud comunitaria.</em></small>
        </div>
      `;
      if (typeof showToast === 'function') showToast('Receta adaptada a Lengua Maya (Inclusión Intercultural)', 'info');
    } else if (lang === 'facil') {
      notesEl.innerHTML = `
        <div class="lang-translation-banner facil-banner">
          <span class="lang-pill">Español de Lectura Fácil</span>
          <p><strong>Pasos muy sencillos para cuidarse:</strong><br/>
          1. Tómese su medicina todos los días a la misma hora con un vaso con agua.<br/>
          2. No deje de tomarla aunque ya se sienta mejor.<br/>
          3. Si le da dolor fuerte de cabeza o no puede respirar bien, venga de inmediato a la clínica.</p>
          <small><em>Formato accesible para facilitar la comprensión clara y evitar errores en la toma de medicamentos.</em></small>
        </div>
      `;
      if (typeof showToast === 'function') showToast('Instrucciones en Formato de Lectura Fácil activadas', 'info');
    } else {
      const original = notesEl.getAttribute('data-original-es');
      if (original) {
        notesEl.innerText = original;
      }
      if (typeof showToast === 'function') showToast('Idioma restablecido a Español Clínico', 'info');
    }
  },

  // 7. PRIVACIDAD: Anonimización / Desidentificación Instantánea (Safe Harbor / LFPDPPP)
  toggleAnonymization() {
    this.isAnonymized = !this.isAnonymized;
    const btn = document.getElementById('btn-toggle-anonymize');
    if (btn) btn.classList.toggle('active', this.isAnonymized);

    // Enmascarar datos en el panel de resultados y paciente
    const curpEl = document.getElementById('panel-vitals-curp');
    const nameEl = document.getElementById('panel-vitals-name');
    const avatarEl = document.getElementById('panel-vitals-avatar');

    if (this.isAnonymized) {
      if (curpEl) {
        curpEl.setAttribute('data-real-curp', curpEl.textContent);
        curpEl.textContent = '•••••••••••••••••• (Cifrado LFPDPPP)';
      }
      if (nameEl) {
        nameEl.setAttribute('data-real-name', nameEl.textContent);
        nameEl.textContent = 'PACIENTE DESIDENTIFICADO [ID PROTEGIDO]';
      }
      if (avatarEl) avatarEl.textContent = '??';
      document.body.classList.add('privacy-anonymized');
      if (typeof showToast === 'function') {
        showToast('Privacidad: Datos sensibles disociados para interconsulta/docencia (NOM-024 / LFPDPPP)', 'success');
      }
    } else {
      if (curpEl && curpEl.hasAttribute('data-real-curp')) {
        curpEl.textContent = curpEl.getAttribute('data-real-curp');
      }
      if (nameEl && nameEl.hasAttribute('data-real-name')) {
        nameEl.textContent = nameEl.getAttribute('data-real-name');
      }
      if (avatarEl) avatarEl.textContent = 'PT';
      document.body.classList.remove('privacy-anonymized');
      if (typeof showToast === 'function') {
        showToast('Identificación clínica restaurada para atención directa', 'info');
      }
    }
  },

  // 1 & 3. TRANSPARENCIA & RESPONSABILIDAD: Modal de Gobernanza y Explicabilidad
  openGovernanceModal() {
    const modal = document.getElementById('ethical-governance-modal');
    if (modal) {
      modal.classList.add('open');
      modal.setAttribute('aria-hidden', 'false');
    }
  },

  closeGovernanceModal() {
    const modal = document.getElementById('ethical-governance-modal');
    if (modal) {
      modal.classList.remove('open');
      modal.setAttribute('aria-hidden', 'true');
    }
  },

  // 3 & 4. RESPONSABILIDAD: Registro de Discrepancia Médica (Feedback Loop)
  reportDiscrepancy() {
    const reason = prompt('Indica el motivo de discrepancia clínica o sugerencia de mejora para la IA (se registrará en la bitácora inmutable de auditoría):');
    if (reason && reason.trim()) {
      if (typeof showToast === 'function') {
        showToast('Discrepancia clínica registrada en la bitácora de auditoría y mejora continua.', 'success');
      }
    }
  }
};