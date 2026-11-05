# 🔮 Future Update: Interoperabilidad Semántica con IA

## Contexto y Visión
MedicAItion actualmente genera expedientes clínicos estandarizados con CIE-10 de forma local.
La siguiente evolución natural es permitir que **dos instituciones médicas intercambien datos
de pacientes sin importar que usen nomenclaturas diferentes en sus sistemas informáticos**,
usando la IA local del proyecto como puente traductor.

---

## El Problema Real
Los hospitales no usan las mismas etiquetas en sus bases de datos:
- Hospital A almacena pacientes bajo el campo `"PACIENTES"`
- Hospital B almacena pacientes bajo el campo `"PERSONAS_ATENDIDAS"`
- El estándar FHIR lo llama `"Patient"`

Un sistema tradicional no puede conectar estos tres porque para una máquina sin IA,
`"PACIENTES"` y `"PERSONAS_ATENDIDAS"` son tan diferentes como `"Perro"` y `"Avión"`.

---

## Solución Propuesta: Middleware Semántico con IA

### Escenario 1: Alguien me pide datos a mí (MedicAItion como Servidor)
1. El Hospital A hace una petición a nuestro endpoint pidiendo el campo `"PERSONAS_ATENDIDAS"`.
2. Nuestro sistema no tiene ese campo, pero antes de devolver un error, le pasa la petición
   al LLM (Med42) con un prompt del tipo:
   > "El cliente solicita 'PERSONAS_ATENDIDAS'. Mi base de datos tiene los campos
   > ['pacientes', 'instituciones', 'medicos']. ¿A cuál equivale semánticamente?"
3. El LLM responde: `"equivale a: pacientes"`.
4. Nuestro sistema extrae los datos de `pacientes` pero los devuelve re-etiquetados como
   `"PERSONAS_ATENDIDAS"` para que el Hospital A los reciba sin errores.

### Escenario 2: Yo pido datos a alguien más (MedicAItion como Cliente)
1. **Fase de Descubrimiento (Schema Discovery):** Antes de pedir datos, MedicAItion le
   solicita al Hospital B su diccionario de campos disponibles (ej. `["NOMBRES", "EDADES",
   "FRUTOS", "DIRECCIONES"]`).
2. **Mapeo Interno con IA:** MedicAItion necesita el campo `"FRUTAS"`. El LLM analiza la
   lista del Hospital B y determina que `"FRUTOS"` es el equivalente semántico.
3. **Petición Traducida:** MedicAItion arma la petición usando la nomenclatura del Hospital B
   (`"FRUTOS"` en vez de `"FRUTAS"`). El servidor del Hospital B la entiende perfectamente.
4. **Recepción y Re-etiquetado:** Los datos llegan con la etiqueta `"FRUTOS"`, y MedicAItion
   los renombra internamente a `"FRUTAS"` para que el resto del software funcione normal.

### Escenario 3: Exportación a Estándar FHIR (HL7 R4)
Como alternativa estática (sin IA en tiempo real), MedicAItion puede exportar un archivo
JSON bajo el estándar internacional FHIR que cualquier hospital moderno puede importar.
Los recursos a generar serían:
- `Patient` → Datos demográficos
- `Condition` → Padecimientos (con código CIE-10)
- `Observation` → Síntomas y notas clínicas
- `MedicationRequest` → Medicamentos recetados

---

## Arquitectura Técnica Propuesta

### Nuevos Archivos a Crear
```
app/
├── core/
│   ├── fhir_exporter.py          # Exportador estático a HL7 FHIR R4
│   └── semantic_middleware.py     # Traductor semántico dinámico con LLM
├── api/
│   ├── routes_interop.py         # Endpoints de intercambio de datos
│   └── routes_schema.py          # Endpoint de Schema Discovery (diccionario de campos)
```

### Flujo del Middleware Semántico
```
Hospital A (petición) ──► /api/interop/query
                              │
                              ▼
                     ¿Campo existe en mi BD?
                        /           \
                      Sí             No
                      │               │
                      ▼               ▼
                  Devolver       Pasar al LLM
                  datos       "¿A qué equivale?"
                                      │
                                      ▼
                                 Mapeo encontrado
                                      │
                                      ▼
                              Devolver datos con
                              etiqueta del solicitante
```

### Flujo del Schema Discovery (Cuando yo pido)
```
MedicAItion ──► GET /api/schema del Hospital B
                              │
                              ▼
                   Recibo lista de campos:
                   ["FRUTOS", "EDADES", ...]
                              │
                              ▼
                   Mi LLM mapea mis campos
                   a los de ellos:
                   FRUTAS → FRUTOS
                              │
                              ▼
                   Armo petición con SUS etiquetas
                   GET /api/data?campo=FRUTOS
                              │
                              ▼
                   Recibo datos y re-etiqueto
                   internamente como FRUTAS
```

---

## Consideraciones Técnicas

### Ventajas
- **Plug & Play:** No requiere que el otro hospital modifique su código.
- **Universalmente Compatible:** La IA se adapta a cualquier nomenclatura.
- **Sin Dependencia de Estándares:** Funciona incluso si ninguno de los dos usa FHIR.

### Desventajas y Retos
- **Velocidad:** FHIR es instantáneo (reglas fijas). El LLM tarda segundos en "pensar".
- **Alucinaciones:** Se necesitan candados estrictos para evitar que el LLM confunda
  `"MÉDICOS"` con `"PACIENTES"` si la petición es ambigua.
- **Seguridad:** Se requiere autenticación robusta (OAuth2 / API Keys) para los endpoints
  de intercambio de datos sensibles de pacientes.
- **Consentimiento:** Cumplir con la Ley Federal de Protección de Datos Personales en
  Posesión de Particulares (LFPDPPP) para el intercambio de datos de salud.

---

## Prioridad de Implementación
1. **Fase 1 (Actual):** Generación de Nota Médica Oficial (NOM-004) con PDF/Impresión.
2. **Fase 2:** Exportador estático a FHIR (sin IA en tiempo real).
3. **Fase 3:** Middleware Semántico con IA (Schema Discovery + Traducción Dinámica).

---

*Documento creado como referencia para futuras actualizaciones del proyecto MedicAItion.*
*Fecha de concepción: Mayo 2026*
