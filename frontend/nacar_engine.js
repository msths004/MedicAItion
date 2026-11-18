/**
 * nacar_engine.js — Motor Bio-Clínico Nácar para MedicAItion
 * ============================================================================
 * Implementa:
 *  1. Preloader clínico (INICIALIZANDO SISTEMA CLÍNICO NOM-004 · 00%..100%)
 *  2. Partículas ambientales 2D bioluminiscentes (#bg-particles) con pausa al perder foco
 *  3. Scrollbar flotante personalizada (.c-scroll / .c-thumb) con arrastre directo
 *  4. Coreografía GSAP + ScrollTrigger (revelado .w > span, tarjetas Bento, contadores y .bf)
 *  5. Cursor magnético contextual (.aww-cursor) + Telemetría HUD (.aww-hud)
 *  6. Visor interactivo 3D / Canvas (.tankbox + #tank-3d) en Herramientas IA
 */
(function () {
  "use strict";

  const $ = (s, root = document) => root.querySelector(s);
  const $$ = (s, root = document) => Array.prototype.slice.call(root.querySelectorAll(s));
  const prefersReduced = () =>
    window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* -------------------------------------------------------------------------
     1. PRELOADER DE INICIALIZACIÓN CLÍNICA (.preloader)
     ------------------------------------------------------------------------- */
  function initPreloader() {
    const preloader = $("#preloader");
    const preBar = $("#pre-bar");
    const preLbl = $("#pre-lbl");
    const loadingScreen = $("#loading-screen");

    if (!preloader) return;

    // Ocultar loading-screen legado inmediatamente para evitar doble cortina
    if (loadingScreen) {
      loadingScreen.classList.add("hidden");
      loadingScreen.style.display = "none";
    }

    if (prefersReduced()) {
      if (preBar) preBar.style.width = "100%";
      if (preLbl) preLbl.textContent = "INICIALIZANDO SISTEMA CLÍNICO NOM-004 · 100%";
      preloader.classList.add("done");
      return;
    }

    const duration = 560;
    const t0 = performance.now();
    function step(now) {
      const k = Math.min((now - t0) / duration, 1);
      const eased = 1 - Math.pow(1 - k, 2);
      const pct = Math.round(eased * 100);
      if (preBar) preBar.style.width = pct + "%";
      if (preLbl) {
        preLbl.textContent = "INICIALIZANDO SISTEMA CLÍNICO NOM-004 · " + String(pct).padStart(2, "0") + "%";
      }
      if (k < 1) {
        requestAnimationFrame(step);
      } else {
        setTimeout(() => preloader.classList.add("done"), 100);
      }
    }
    requestAnimationFrame(step);
  }

  function triggerClinicalNodePreloader(nodeLabel) {
    const preloader = $("#preloader");
    const preBar = $("#pre-bar");
    const preLbl = $("#pre-lbl");
    if (!preloader || prefersReduced()) return;

    const label = (nodeLabel || "SINCRONIZANDO NODO HOSPITALARIO NOM-024").toUpperCase();
    preloader.classList.remove("done", "hide");
    if (preBar) preBar.style.width = "0%";

    const duration = 420;
    const t0 = performance.now();
    function step(now) {
      const k = Math.min((now - t0) / duration, 1);
      const pct = Math.round(k * 100);
      if (preBar) preBar.style.width = pct + "%";
      if (preLbl) preLbl.textContent = `${label} · ${String(pct).padStart(2, "0")}%`;
      if (k < 1) requestAnimationFrame(step);
      else setTimeout(() => preloader.classList.add("done"), 80);
    }
    requestAnimationFrame(step);
  }

  /* -------------------------------------------------------------------------
     2. CANVAS AMBIENTAL LIGERO (#bg-particles)
     ------------------------------------------------------------------------- */
  function initAmbientParticles() {
    const canvas = $("#bg-particles");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    let W = 0;
    let H = 0;
    let dpr = 1;
    let mx = 0;
    let my = 0;
    let tmx = 0;
    let tmy = 0;
    let paused = false;

    const count = 42;
    const particles = [];
    for (let i = 0; i < count; i++) {
      particles.push({
        x: Math.random(),
        y: Math.random(),
        r: 0.9 + Math.random() * 2.1,
        vx: (Math.random() - 0.5) * 0.00022,
        vy: -0.00018 - Math.random() * 0.00032,
        alpha: 0.18 + Math.random() * 0.45,
        depth: 0.3 + Math.random() * 0.9,
        phase: Math.random() * Math.PI * 2,
      });
    }

    function resize() {
      dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      W = canvas.width = Math.floor(window.innerWidth * dpr);
      H = canvas.height = Math.floor(window.innerHeight * dpr);
    }
    resize();
    window.addEventListener("resize", resize, { passive: true });
    window.addEventListener(
      "pointermove",
      (e) => {
        tmx = (e.clientX / Math.max(window.innerWidth, 1) - 0.5) * 2;
        tmy = (e.clientY / Math.max(window.innerHeight, 1) - 0.5) * 2;
      },
      { passive: true }
    );
    document.addEventListener("visibilitychange", () => {
      paused = document.hidden;
    });

    function drawFrame(now) {
      requestAnimationFrame(drawFrame);
      if (paused || prefersReduced()) return;

      mx += (tmx - mx) * 0.04;
      my += (tmy - my) * 0.04;

      ctx.clearRect(0, 0, W, H);
      const isLight = document.documentElement.getAttribute("data-theme") === "light";
      const t = now * 0.001;

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.x += p.vx;
        p.y += p.vy;
        if (p.y < -0.04) {
          p.y = 1.04;
          p.x = Math.random();
        }
        if (p.x < -0.04) p.x = 1.04;
        if (p.x > 1.04) p.x = -0.04;

        const px = (p.x + mx * 0.018 * p.depth) * W;
        const py = (p.y + my * 0.018 * p.depth) * H;
        const flicker = 0.65 + 0.35 * Math.sin(t * 1.4 + p.phase);
        const rad = p.r * dpr;

        ctx.beginPath();
        ctx.arc(px, py, rad, 0, Math.PI * 2);
        ctx.fillStyle = isLight
          ? `rgba(11, 110, 120, ${(p.alpha * flicker * 0.55).toFixed(3)})`
          : `rgba(124, 224, 244, ${(p.alpha * flicker).toFixed(3)})`;
        ctx.fill();
      }
    }

    if (!prefersReduced()) {
      requestAnimationFrame(drawFrame);
    }
  }

  /* -------------------------------------------------------------------------
     3. SCROLLBAR FLOTANTE PERSONALIZADA (.c-scroll / .c-thumb)
     ------------------------------------------------------------------------- */
  let refreshScrollbar = () => {};

  function initFloatingScrollbar() {
    const track = $("#c-scroll");
    const thumb = $("#c-thumb");
    if (!track || !thumb) return;

    let dragActive = false;
    let grabOffsetY = 0;

    function getScroller() {
      const wrapper = $(".app-main-wrapper");
      if (wrapper && wrapper.scrollHeight > wrapper.clientHeight + 4) {
        return wrapper;
      }
      return document.scrollingElement || document.documentElement;
    }

    function getMetrics() {
      const scroller = getScroller();
      const maxScroll = Math.max(0, scroller.scrollHeight - scroller.clientHeight);
      const scrollTop = scroller.scrollTop || 0;
      const trackH = track.clientHeight || Math.max(window.innerHeight - 126, 120);
      const thumbH = Math.max(40, Math.min(84, (scroller.clientHeight / Math.max(scroller.scrollHeight, 1)) * trackH));
      return { scroller, maxScroll, scrollTop, trackH, thumbH };
    }

    function updateThumbPosition() {
      const { maxScroll, scrollTop, trackH, thumbH } = getMetrics();
      if (maxScroll <= 2) {
        thumb.style.opacity = "0";
        thumb.style.pointerEvents = "none";
        return;
      }
      thumb.style.opacity = "1";
      thumb.style.pointerEvents = "auto";
      thumb.style.height = thumbH.toFixed(0) + "px";

      const ratio = Math.max(0, Math.min(1, scrollTop / maxScroll));
      const maxTravel = Math.max(0, trackH - thumbH);
      const y = ratio * maxTravel;
      thumb.style.transform = `translate3d(0, ${y.toFixed(1)}px, 0)`;
    }

    refreshScrollbar = updateThumbPosition;

    const wrapper = $(".app-main-wrapper");
    if (wrapper) {
      wrapper.addEventListener("scroll", () => {
        if (!dragActive) updateThumbPosition();
      }, { passive: true });
    }
    window.addEventListener("scroll", () => {
      if (!dragActive) updateThumbPosition();
    }, { passive: true });
    window.addEventListener("resize", updateThumbPosition, { passive: true });

    thumb.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      e.stopPropagation();
      dragActive = true;
      thumb.classList.add("dragging");
      grabOffsetY = e.clientY - thumb.getBoundingClientRect().top;
      if (thumb.setPointerCapture) {
        thumb.setPointerCapture(e.pointerId);
      }
    });

    thumb.addEventListener("pointermove", (e) => {
      if (!dragActive) return;
      const tr = track.getBoundingClientRect();
      const { scroller, maxScroll, thumbH } = getMetrics();
      const maxTravel = Math.max(1, tr.height - thumbH);
      const ratio = Math.max(0, Math.min(1, (e.clientY - tr.top - grabOffsetY) / maxTravel));
      scroller.scrollTop = ratio * maxScroll;
      thumb.style.transform = `translate3d(0, ${(ratio * maxTravel).toFixed(1)}px, 0)`;
    });

    const endDrag = () => {
      if (!dragActive) return;
      dragActive = false;
      thumb.classList.remove("dragging");
    };
    thumb.addEventListener("pointerup", endDrag);
    thumb.addEventListener("pointercancel", endDrag);

    updateThumbPosition();
  }

  /* -------------------------------------------------------------------------
     4. COREOGRAFÍA DE ANIMACIONES (GSAP + Fallback Nativo)
     ------------------------------------------------------------------------- */
  function animateCounterEl(el) {
    if (!el || el.dataset.nacarCounted === "1") return;
    el.dataset.nacarCounted = "1";

    const end = parseFloat(el.dataset.n);
    if (isNaN(end)) return;
    const dec = parseInt(el.dataset.d || "0", 10);
    const prefix = el.dataset.p || "";
    const suffix = el.dataset.s || "";

    if (prefersReduced()) {
      el.textContent = prefix + end.toFixed(dec) + suffix;
      return;
    }

    const t0 = performance.now();
    const dur = 1100;
    function tick(now) {
      const k = Math.min((now - t0) / dur, 1);
      const eased = 1 - Math.pow(1 - k, 3);
      const val = (end * eased).toFixed(dec);
      el.textContent = prefix + val + suffix;
      if (k < 1) requestAnimationFrame(tick);
      else el.textContent = prefix + end.toFixed(dec) + suffix;
    }
    requestAnimationFrame(tick);
  }

  function animateBarsInRoot(root) {
    const bars = $$(".bf, .kpi-progress-bar", root || document);
    bars.forEach((b) => {
      const targetW = b.dataset.w ? b.dataset.w + "%" : b.style.width || "0%";
      if (prefersReduced()) {
        b.style.width = targetW;
        return;
      }
      if (!b.dataset.w && b.style.width) {
        b.dataset.w = b.style.width.replace("%", "");
      }
      b.style.width = "0%";
      requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          b.style.width = (b.dataset.w || "0") + "%";
        });
      });
    });
  }

  function splitHeadingWords(el) {
    if (!el || el.dataset.nacarSplit === "1") return;
    el.dataset.nacarSplit = "1";
    const text = (el.textContent || "").trim();
    if (!text) return;
    el.innerHTML = text
      .split(/\s+/)
      .map((w) => `<span class="w"><span>${w}</span></span>`)
      .join(" ");
  }

  function animateViewEntrance(panelRoot) {
    const scope = panelRoot || document;
    const counters = $$("[data-n]", scope);
    counters.forEach((c) => {
      c.dataset.nacarCounted = "0";
      animateCounterEl(c);
    });
    animateBarsInRoot(scope);

    if (prefersReduced() || !window.gsap) return;

    const headings = $$("h1.modular-page-title, h1.patients-page-title, h1.agenda-page-title, .reports-header h1, .tools-header h1, .red-header-text h1", scope);
    headings.forEach((h) => {
      splitHeadingWords(h);
      const spans = $$(".w > span", h);
      if (spans.length) {
        window.gsap.fromTo(
          spans,
          { yPercent: 115, opacity: 0 },
          {
            yPercent: 0,
            opacity: 1,
            duration: 0.72,
            ease: "expo.out",
            stagger: 0.045,
            clearProps: "transform,opacity",
            onComplete: () => $$(".w", h).forEach((w) => w.classList.add("done")),
          }
        );
      }
    });

    const cards = $$(".modular-card, .bento-card", scope).filter((c) => c.offsetParent !== null);
    if (cards.length) {
      window.gsap.fromTo(
        cards,
        { y: 18, opacity: 0 },
        {
          y: 0,
          opacity: 1,
          duration: 0.65,
          stagger: 0.055,
          ease: "expo.out",
          overwrite: "auto",
          clearProps: "transform,opacity",
        }
      );
    }
  }

  function initChoreography() {
    if (window.gsap && window.ScrollTrigger) {
      window.gsap.registerPlugin(window.ScrollTrigger);
    }
    animateViewEntrance($("#panel-dashboard-section") || document);
  }

  /* -------------------------------------------------------------------------
     5. CURSOR MAGNÉTICO CONTEXTUAL (.aww-cursor) + TELEMETRÍA HUD (.aww-hud)
     ------------------------------------------------------------------------- */
  function initCursorAndHud() {
    const cursor = $("#aww-cursor");
    const labelEl = $("#aww-lbl");
    const hudView = $("#hud-view-state");

    if (cursor && window.matchMedia && window.matchMedia("(hover: hover) and (min-width: 900px)").matches) {
      let cx = window.innerWidth * 0.5;
      let cy = window.innerHeight * 0.5;
      let tcx = cx;
      let tcy = cy;
      let active = true;

      window.addEventListener(
        "pointermove",
        (e) => {
          tcx = e.clientX;
          tcy = e.clientY;
        },
        { passive: true }
      );

      document.addEventListener("visibilitychange", () => {
        active = !document.hidden;
      });

      function tickCursor() {
        requestAnimationFrame(tickCursor);
        if (!active || prefersReduced()) return;
        cx += (tcx - cx) * 0.18;
        cy += (tcy - cy) * 0.18;
        cursor.style.transform = `translate3d(${cx.toFixed(1)}px, ${cy.toFixed(1)}px, 0)`;
      }
      requestAnimationFrame(tickCursor);

      // Etiquetas contextuales dinámicas por delegación (resiste elementos inyectados dinámicamente)
      const cursorTargets = [
        { match: "#pulso-fab-btn", label: "ASISTENTE IA" },
        { match: "#tank-3d", label: "ROTAR 3D" },
        { match: "#nav-btn-consulta, button[onclick*=\"switchMainTab('consulta')\"]", label: "CONSULTAR" },
        { match: "#dashboard-patient-select, .modular-patient-picker, #consulta-patient-dropdown, #ask-patient-select, #lab-patient-select", label: "CAMBIAR" },
        { match: "#nav-btn-labs, button[onclick*=\"openLaboratorioModal\"]", label: "LABS" },
        { match: "#nav-btn-red-hospitalaria, .hospital-network-pill", label: "7 NODOS" },
        { match: "#theme-toggle-btn", label: "TEMA" },
        { match: "#submit-btn", label: "PROCESAR IA" },
      ];

      document.addEventListener(
        "pointerover",
        (e) => {
          const target = e.target;
          if (!target || !target.closest) return;
          for (let i = 0; i < cursorTargets.length; i++) {
            const rule = cursorTargets[i];
            if (target.closest(rule.match)) {
              cursor.classList.add("expand");
              if (labelEl) labelEl.textContent = rule.label;
              return;
            }
          }
        },
        { passive: true }
      );

      document.addEventListener(
        "pointerout",
        (e) => {
          const target = e.target;
          const related = e.relatedTarget;
          if (!target || !target.closest) return;
          for (let i = 0; i < cursorTargets.length; i++) {
            const matched = target.closest(cursorTargets[i].match);
            if (matched && (!related || !matched.contains(related))) {
              cursor.classList.remove("expand");
              if (labelEl) labelEl.textContent = "";
              return;
            }
          }
        },
        { passive: true }
      );
    }

    if (hudView) {
      updateHudForTab(window.AppState?.mainTab || "dashboard");
    }
  }

  function updateHudForTab(tab) {
    const hudView = $("#hud-view-state");
    if (!hudView) return;
    const labels = {
      dashboard: "RESUMEN EJECUTIVO · RED YUCATÁN (7 NODOS)",
      consulta: "NUEVA CONSULTA NOM-004 · CIE-10 ACTIVO",
      expedientes: "DIRECTORIO DE PACIENTES · CIFRADO LOCAL",
      expediente: "EXPEDIENTE ESPECIALIZADO SOAP · NOM-024",
      agenda: "AGENDA CLÍNICA ANUAL · MÉRIDA",
      herramientas: "HERRAMIENTAS IA · GEMELO BIO-CLÍNICO 3D",
      "red-hospitalaria": "RED INTERHOSPITALARIA FEDERADA · 7 NODOS EN LÍNEA",
      reportes: "VIGILANCIA EPIDEMIOLÓGICA SINAVE",
      legal: "LFPDPPP · DERECHOS ARCO & CHACHA20",
      config: "RBAC · AUDITORÍA NOM-024",
    };
    hudView.textContent = labels[tab] || "SISTEMA CLÍNICO NOM-004 · 7 NODOS EN LÍNEA";
  }

  /* -------------------------------------------------------------------------
     6. MÓDULO VISOR INTERACTIVO 3D / CANVAS (.tankbox + #tank-3d)
     ------------------------------------------------------------------------- */
  let _tankMode = "none";
  let _tankFallbackStop = null;
  let _tankResizeFn = null;

  function initTankViewer() {
    if (_tankMode === "3d") return;
    let canvas = $("#tank-3d");
    if (!canvas) return;
    const box = $("#tankbox");

    const stageCaptions = [
      "Fase 1 · Perfil Hematológico & Constantes Basales (Triaje)",
      "Fase 2 · Aislamiento Terapéutico & Barrera de Alergias CDSS",
      "Fase 3 · Bio-Sinergia Farmacológica & Farmacocinética Renal",
      "Fase 4 · Telemetría IoT + Digital Twin Predictivo NOM-024",
      "Fase 5 · Estabilización & Remisión Clínica Verificada",
    ];
    const captionEl = $("#tank-stage-label");
    let currentStage = 0;

    // Fallback 2D limpio en caso de no existir WebGL / Three.js (100% resiliente offline)
    if (!window.THREE) {
      if (_tankMode === "none") {
        _tankMode = "2d";
        initTankViewer2DFallback(canvas, box, captionEl, stageCaptions);
      }
      return;
    }

    // Si existía contexto 2D previo, reemplazar el canvas para permitir contexto WebGL limpio
    if (_tankMode === "2d") {
      if (typeof _tankFallbackStop === "function") _tankFallbackStop();
      const fresh = document.createElement("canvas");
      fresh.id = "tank-3d";
      fresh.setAttribute("role", canvas.getAttribute("role") || "img");
      fresh.setAttribute("aria-label", canvas.getAttribute("aria-label") || "Visor 3D interactivo");
      canvas.parentNode.replaceChild(fresh, canvas);
      canvas = fresh;
    }

    let renderer;
    try {
      renderer = new window.THREE.WebGLRenderer({ canvas, alpha: true, antialias: true, powerPreference: "high-performance" });
    } catch {
      if (_tankMode !== "2d") {
        _tankMode = "2d";
        initTankViewer2DFallback(canvas, box, captionEl, stageCaptions);
      }
      return;
    }

    _tankMode = "3d";
    const THREE = window.THREE;
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(38, 1, 0.1, 100);

    function resize() {
      const r = canvas.getBoundingClientRect();
      const w = Math.max(r.width, 280);
      const h = Math.max(r.height, 260);
      renderer.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
    }
    _tankResizeFn = resize;
    resize();
    window.addEventListener("resize", resize, { passive: true });

    const dirL1 = new THREE.DirectionalLight(0xffffff, 2.2);
    dirL1.position.set(6, 10, 7);
    const dirL2 = new THREE.DirectionalLight(0x7ce0f4, 1.5);
    dirL2.position.set(-6, 5, -6);
    const amb = new THREE.AmbientLight(0x8ab8cc, 1.1);
    scene.add(dirL1, dirL2, amb);

    const diorama = new THREE.Group();
    scene.add(diorama);

    // Base celular / anatómica kárstica translúcida
    const baseGeo = new THREE.BoxGeometry(4.2, 0.7, 4.2, 18, 4, 18);
    const baseMat = new THREE.MeshStandardMaterial({
      color: 0x0b2234,
      roughness: 0.72,
      metalness: 0.18,
    });
    const baseMesh = new THREE.Mesh(baseGeo, baseMat);
    baseMesh.position.y = -1.1;
    diorama.add(baseMesh);

    // Cubo fluido bio-clínico con ola dinámica superior
    const W_SIZE = 4.1;
    const WATER_BOT = -0.72;
    const WATER_TOP_BASE = 0.85;
    const GRID_SEG = 26;

    const stagePresets = [
      { r: 0.18, g: 0.44, b: 0.56, opacity: 0.82, nodesVisible: true, hudOpacity: 0.25 },
      { r: 0.12, g: 0.56, b: 0.68, opacity: 0.74, nodesVisible: true, hudOpacity: 0.45 },
      { r: 0.16, g: 0.68, b: 0.78, opacity: 0.62, nodesVisible: true, hudOpacity: 0.68 },
      { r: 0.28, g: 0.78, b: 0.90, opacity: 0.50, nodesVisible: true, hudOpacity: 0.92 },
      { r: 0.42, g: 0.88, b: 0.98, opacity: 0.38, nodesVisible: true, hudOpacity: 0.35 },
    ];

    const waterState = { ...stagePresets[0] };
    const fluidMat = new THREE.MeshPhysicalMaterial({
      color: new THREE.Color(waterState.r, waterState.g, waterState.b),
      roughness: 0.12,
      metalness: 0.08,
      clearcoat: 1.0,
      transparent: true,
      opacity: waterState.opacity,
      side: THREE.DoubleSide,
      depthWrite: false,
    });

    const topGeo = new THREE.PlaneGeometry(W_SIZE, W_SIZE, GRID_SEG, GRID_SEG);
    topGeo.rotateX(-Math.PI / 2);
    const topMesh = new THREE.Mesh(topGeo, fluidMat);
    diorama.add(topMesh);

    const cageMat = new THREE.LineBasicMaterial({ color: 0x7ce0f4, transparent: true, opacity: 0.45 });
    const cage = new THREE.LineSegments(
      new THREE.EdgesGeometry(new THREE.BoxGeometry(W_SIZE + 0.04, 1.7, W_SIZE + 0.04)),
      cageMat
    );
    cage.position.y = 0.08;
    diorama.add(cage);

    const scanMat = new THREE.MeshBasicMaterial({
      color: 0xb8ecff,
      wireframe: true,
      transparent: true,
      opacity: 0.35,
    });
    const scanPlane = new THREE.Mesh(new THREE.PlaneGeometry(W_SIZE, W_SIZE, 10, 10), scanMat);
    scanPlane.rotation.x = -Math.PI / 2;
    diorama.add(scanPlane);

    // Nodos bio-vitales flotantes (corazón, perfusión renal, homeostasis)
    const nodes = [];
    const nodeGeo = new THREE.SphereGeometry(0.14, 16, 16);
    const nodeMat = new THREE.MeshPhysicalMaterial({
      color: 0xffffff,
      emissive: 0x7ce0f4,
      emissiveIntensity: 0.55,
      roughness: 0.15,
    });
    for (let i = 0; i < 7; i++) {
      const m = new THREE.Mesh(nodeGeo, nodeMat);
      const ang = (i / 7) * Math.PI * 2;
      const rad = i === 0 ? 0 : 1.25;
      m.position.set(Math.cos(ang) * rad, 0.05, Math.sin(ang) * rad);
      nodes.push({ mesh: m, baseX: Math.cos(ang) * rad, baseZ: Math.sin(ang) * rad, phase: i * 0.9 });
      diorama.add(m);
    }

    function waveH(x, z, t) {
      return (
        WATER_TOP_BASE +
        Math.sin(x * 1.45 + t * 2.1) * Math.cos(z * 1.25 + t * 1.7) * 0.09 +
        Math.sin((x - z) * 1.1 + t * 2.6) * 0.045
      );
    }

    let rotY = -0.6;
    let rotX = 0.42;
    let tRotY = -0.6;
    let tRotX = 0.42;
    let zoom = 9.0;
    let tZoom = 9.0;
    let dragging = false;
    let prevX = 0;
    let prevY = 0;
    let isVisible = false;
    let clock = 0;

    canvas.addEventListener("pointerdown", (e) => {
      dragging = true;
      prevX = e.clientX;
      prevY = e.clientY;
      if (canvas.setPointerCapture) canvas.setPointerCapture(e.pointerId);
    });
    canvas.addEventListener("pointermove", (e) => {
      if (!dragging) return;
      const dx = e.clientX - prevX;
      const dy = e.clientY - prevY;
      prevX = e.clientX;
      prevY = e.clientY;
      tRotY += dx * 0.009;
      tRotX = Math.max(-0.05, Math.min(1.18, tRotX + dy * 0.008));
    });
    const endDrag = () => { dragging = false; };
    canvas.addEventListener("pointerup", endDrag);
    canvas.addEventListener("pointercancel", endDrag);

    if (box) {
      box.addEventListener(
        "wheel",
        (e) => {
          e.preventDefault();
          e.stopPropagation();
          tZoom = Math.max(5.2, Math.min(13.8, tZoom + (e.deltaY > 0 ? 0.7 : -0.7)));
        },
        { passive: false }
      );
    }

    const dots = $$("#tank-dots span");
    function setStage(idx) {
      currentStage = Math.max(0, Math.min(4, idx));
      dots.forEach((d, k) => d.classList.toggle("on", k === currentStage));
      if (captionEl) captionEl.textContent = stageCaptions[currentStage];
      const p = stagePresets[currentStage];
      if (window.gsap) {
        window.gsap.to(waterState, {
          r: p.r,
          g: p.g,
          b: p.b,
          opacity: p.opacity,
          hudOpacity: p.hudOpacity,
          duration: 0.55,
          ease: "power3.out",
        });
      } else {
        Object.assign(waterState, p);
      }
      renderFrame(true);
    }

    dots.forEach((d, k) => d.addEventListener("click", () => setStage(k)));
    $("#z-in")?.addEventListener("click", () => { tZoom = Math.max(5.2, tZoom - 1.0); });
    $("#z-out")?.addEventListener("click", () => { tZoom = Math.min(13.8, tZoom + 1.0); });
    $("#z-rst")?.addEventListener("click", () => {
      tRotY = -0.6;
      tRotX = 0.42;
      tZoom = 9.0;
      setStage(0);
    });

    if (window.IntersectionObserver) {
      new IntersectionObserver((es) => {
        isVisible = es[0].isIntersecting;
      }, { threshold: 0.05 }).observe(canvas);
    } else {
      isVisible = true;
    }

    function renderFrame(forceOnce) {
      if (!forceOnce && (!isVisible || document.hidden || prefersReduced())) return;
      clock += prefersReduced() ? 0 : 0.016;
      if (!dragging && !prefersReduced()) tRotY += 0.0018;

      rotY += (tRotY - rotY) * 0.1;
      rotX += (tRotX - rotX) * 0.1;
      zoom += (tZoom - zoom) * 0.1;

      camera.position.x = Math.sin(rotY) * Math.cos(rotX) * zoom;
      camera.position.y = Math.sin(rotX) * zoom;
      camera.position.z = Math.cos(rotY) * Math.cos(rotX) * zoom;
      camera.lookAt(0, -0.1, 0);

      fluidMat.color.setRGB(waterState.r, waterState.g, waterState.b);
      fluidMat.opacity = waterState.opacity;
      cageMat.opacity = 0.2 + waterState.hudOpacity * 0.55;
      scanMat.opacity = waterState.hudOpacity * 0.45;

      const arr = topGeo.attributes.position.array;
      for (let i = 0; i < arr.length; i += 3) {
        arr[i + 1] = waveH(arr[i], arr[i + 2], clock);
      }
      topGeo.attributes.position.needsUpdate = true;
      topGeo.computeVertexNormals();

      scanPlane.position.y = WATER_BOT + ((Math.sin(clock * 1.6) * 0.5 + 0.5) * (WATER_TOP_BASE - WATER_BOT));

      nodes.forEach((n) => {
        n.mesh.position.y = Math.sin(clock * 1.8 + n.phase) * 0.25;
      });

      renderer.render(scene, camera);
    }

    function loop() {
      requestAnimationFrame(loop);
      renderFrame(false);
    }
    renderFrame(true);
    if (!prefersReduced()) requestAnimationFrame(loop);

    setStage(0);
  }

  function initTankViewer2DFallback(canvas, box, captionEl, stageCaptions) {
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    let rot = 0.6;
    let zoom = 1;
    let currentStage = 0;
    let dragging = false;
    let prevX = 0;
    let stopped = false;

    _tankFallbackStop = () => {
      stopped = true;
      window.removeEventListener("resize", resize);
    };

    function resize() {
      const r = canvas.getBoundingClientRect();
      canvas.width = Math.max(r.width, 280);
      canvas.height = Math.max(r.height, 260);
    }
    _tankResizeFn = resize;
    resize();
    window.addEventListener("resize", resize, { passive: true });

    canvas.addEventListener("pointerdown", (e) => {
      dragging = true;
      prevX = e.clientX;
      if (canvas.setPointerCapture) canvas.setPointerCapture(e.pointerId);
    });
    canvas.addEventListener("pointermove", (e) => {
      if (!dragging) return;
      rot += (e.clientX - prevX) * 0.01;
      prevX = e.clientX;
    });
    const end = () => { dragging = false; };
    canvas.addEventListener("pointerup", end);
    canvas.addEventListener("pointercancel", end);

    const dots = $$("#tank-dots span");
    function setStage(i) {
      currentStage = Math.max(0, Math.min(4, i));
      dots.forEach((d, k) => d.classList.toggle("on", k === currentStage));
      if (captionEl) captionEl.textContent = stageCaptions[currentStage];
    }
    dots.forEach((d, k) => d.addEventListener("click", () => setStage(k)));
    $("#z-in")?.addEventListener("click", () => { zoom = Math.min(1.6, zoom + 0.15); });
    $("#z-out")?.addEventListener("click", () => { zoom = Math.max(0.7, zoom - 0.15); });
    $("#z-rst")?.addEventListener("click", () => { zoom = 1; rot = 0.6; setStage(0); });

    function draw(now) {
      if (stopped) return;
      requestAnimationFrame(draw);
      if (document.hidden) return;
      if (!dragging && !prefersReduced()) rot += 0.005;
      const w = canvas.width;
      const h = canvas.height;
      ctx.clearRect(0, 0, w, h);

      const cx = w / 2;
      const cy = h / 2;
      const rx = 110 * zoom;
      const ry = 48 * zoom;
      const t = now * 0.002;

      for (let layer = 0; layer < 3; layer++) {
        const yOff = (layer - 1) * 44 * zoom + Math.sin(t + layer) * 4;
        ctx.beginPath();
        ctx.ellipse(cx, cy + yOff, rx, ry, Math.sin(rot) * 0.15, 0, Math.PI * 2);
        ctx.strokeStyle = layer === currentStage % 3 ? "#7CE0F4" : "rgba(184, 236, 255, 0.35)";
        ctx.lineWidth = layer === 1 ? 2.2 : 1.3;
        ctx.stroke();
      }
    }
    requestAnimationFrame(draw);
    setStage(0);
  }

  /* -------------------------------------------------------------------------
     API PÚBLICA DEL MOTOR NÁCAR
     ------------------------------------------------------------------------- */
  window.NacarEngine = {
    onTabChange(tab) {
      updateHudForTab(tab);
      const map = {
        dashboard: "#panel-dashboard-section",
        consulta: "#consulta-layout",
        expedientes: "#panel-patients-section",
        expediente: "#panel-expediente-section",
        agenda: "#panel-agenda-section",
        reportes: "#panel-reports-section",
        herramientas: "#panel-herramientas-section",
        config: "#panel-config-section",
        legal: "#panel-legal-section",
        "red-hospitalaria": "#panel-red-hospitalaria-section",
      };
      const panelEl = map[tab] ? $(map[tab]) : null;
      if (panelEl) animateViewEntrance(panelEl);
      if (tab === "herramientas" && typeof _tankResizeFn === "function") {
        setTimeout(_tankResizeFn, 40);
      }
      setTimeout(refreshScrollbar, 120);
    },
    onVendorLoaded() {
      if (window.gsap && window.ScrollTrigger) {
        try { window.gsap.registerPlugin(window.ScrollTrigger); } catch {}
      }
      if (window.THREE && _tankMode !== "3d") {
        initTankViewer();
      }
    },
    refreshScrollbar,
    triggerNodePreloader: triggerClinicalNodePreloader,
  };
  window.triggerClinicalNodePreloader = triggerClinicalNodePreloader;

  function boot() {
    initPreloader();
    initAmbientParticles();
    initFloatingScrollbar();
    initCursorAndHud();
    initChoreography();
    initTankViewer();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
