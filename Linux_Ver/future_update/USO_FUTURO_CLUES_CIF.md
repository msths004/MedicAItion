# 🔮 Uso Futuro: CLUES y CIF en MedicAItion

> Este documento describe la utilidad estratégica de los catálogos de **CLUES** (Establecimientos de Salud) y **CIF** (Clasificación Internacional del Funcionamiento) que aún no están integrados al pipeline actual pero que se incorporarán en fases posteriores.

---

## 📍 CLUES — Clave Única de Establecimientos de Salud

### ¿Qué es?
El catálogo CLUES es el directorio oficial de la Secretaría de Salud que contiene **63,595 establecimientos** de salud en todo México. Cada registro incluye:

- **CLUES** — Identificador único de 11 caracteres (ej. `ASCRO000012`)
- **Nombre de la institución** — "Cruz Roja Mexicana"
- **Ubicación** — Entidad, municipio, localidad, dirección, coordenadas GPS
- **Tipo** — Hospital, clínica, consultorio, unidad móvil, etc.
- **Horarios** — Días y horas de operación
- **Servicios** — Áreas y servicios disponibles (banco de sangre, urgencias, etc.)
- **Estatus** — Activo, en construcción, baja, etc.

### ¿Para qué nos servirá?

#### 1. Validación de la institución al registrar expedientes
Actualmente, el campo `CLUES` en el formulario es un input libre. El médico puede escribir cualquier texto. Con el catálogo CLUES podríamos:
- **Autocompletar** el nombre de la institución al escribir la CLUES
- **Validar** que la CLUES existe realmente en el directorio oficial
- **Auto-rellenar** dirección, municipio, entidad y tipo de establecimiento en la nota médica

#### 2. Sistema de búsqueda de pacientes entre instituciones
Cuando MedicAItion se despliegue en múltiples sedes de Cruz Roja, el catálogo CLUES permitirá:
- **Filtrar expedientes por institución** (ej. "todos los pacientes atendidos en Cruz Roja Mérida")
- **Transferencias de pacientes** — Al referir un paciente a otro establecimiento, el sistema puede buscar la unidad receptora por nombre, municipio o servicios disponibles
- **Geolocalización** — Usando las coordenadas GPS del catálogo, mostrar un mapa de establecimientos cercanos para referir al paciente

#### 3. Reportes epidemiológicos por región
Cruzar los diagnósticos CIE-10 de los expedientes con la ubicación geográfica de la CLUES para generar mapas de calor de morbilidad por municipio, entidad o región.

#### 4. Interoperabilidad con sistemas federales
La CLUES es el estándar nacional de identificación de establecimientos. Cualquier integración futura con SINBA, SUAVE, SEED o plataformas de la Secretaría de Salud requerirá enviar la CLUES validada.

### Implementación sugerida
```
Fase 1: Importar el XLSX a una tabla SQLite "establecimientos"
Fase 2: Agregar autocompletado en el frontend (dropdown con búsqueda)
Fase 3: Validación server-side del CLUES en routes_input.py
Fase 4: Vista de mapa con establecimientos cercanos (usando Leaflet.js)
```

---

## 🧠 CIF — Clasificación Internacional del Funcionamiento, Discapacidad y Salud

### ¿Qué es?
La CIF es una clasificación de la OMS que complementa al CIE-10. Mientras el CIE-10 describe **QUÉ enfermedad tiene** el paciente, el CIF describe **CÓMO le afecta funcionalmente**:

- **Funciones corporales** (b) — Estado de conciencia, orientación, memoria, dolor, etc.
- **Estructuras corporales** (s) — Cerebro, extremidades, órganos
- **Actividades y participación** (d) — Caminar, hablar, trabajar, interactuar socialmente
- **Factores ambientales** (e) — Productos, tecnología, apoyo social

### ¿Para qué nos servirá?

#### 1. Evaluación integral del paciente (modelo biopsicosocial)
El CIE-10 dice "El paciente tiene I10 (Hipertensión)". El CIF agrega:
- `b4200` — Presión arterial elevada (función corporal afectada)
- `d920` — Dificultad para recreación y ocio (impacto en vida diaria)
- `e1101` — Medicamentos (factor ambiental facilitador)

Esto permite una visión **holística** del impacto de la enfermedad en la vida del paciente.

#### 2. Seguimiento funcional a lo largo del tiempo
Mientras los diagnósticos CIE-10 suelen ser estáticos ("hipertensión es hipertensión"), los códigos CIF cambian con la evolución del paciente:
- Consulta 1: `d450.3` — Dificultad grave para caminar
- Consulta 3: `d450.1` — Dificultad leve para caminar
- Consulta 5: `d450.0` — Sin dificultad para caminar

Esto permite **medir objetivamente** la rehabilitación y la eficacia del tratamiento.

#### 3. Reportes de discapacidad y rehabilitación
Para pacientes con secuelas (accidentes, ACV, fracturas), el CIF permitiría generar reportes estandarizados de discapacidad que son requeridos por:
- IMSS/ISSSTE para dictámenes de incapacidad
- DIF para programas de rehabilitación
- Tribunales para peritajes médico-legales

#### 4. Integración con el prompt del LLM
El LLM podría extraer automáticamente indicadores CIF del texto médico:
> "El paciente refiere que ya no puede subir escaleras y tiene dificultad para vestirse solo"
> → `d4551` — Dificultad para subir (actividad)
> → `d540` — Dificultad para vestirse (autocuidado)

### Implementación sugerida
```
Fase 1: Ingestar CIF.xlsx en ChromaDB (ya está preparado en el pipeline)
Fase 2: Agregar categoría "funcionalidad" al SYSTEM_PROMPT del LLM
Fase 3: Mostrar códigos CIF junto a los CIE-10 en la nota médica
Fase 4: Dashboard de seguimiento funcional por paciente
```

---

## Prioridad de Implementación

| Catálogo | Prioridad | Razón |
|----------|-----------|-------|
| **CLUES** | Alta (Fase 2) | Necesario para el sistema multi-sede de búsqueda de pacientes |
| **CIF** | Media (Fase 3) | Enriquece la evaluación clínica pero no es requisito de la NOM-004 |

---

*Documento generado para MedicAItion v2.0 — Cruz Roja Mérida*
