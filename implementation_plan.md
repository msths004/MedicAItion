# Instalación Autónoma (Python Portable)

El usuario final (médicos, paramédicos) no debería lidiar con versiones de Python, variables de entorno, o errores de compiladores C++. Debe ser una experiencia de "descargar y ejecutar".

Para garantizar una compatibilidad del 100% en cualquier computadora con Windows, hemos rediseñado cómo arranca la aplicación utilizando un **Python "Embeddable" (Portable)**.

## ¿Cómo funciona el nuevo `run.bat`?
1. Ya no obligamos al usuario a instalar Python globalmente en su sistema.
2. Cuando el usuario hace doble clic en `run.bat`, el archivo verifica si ya tenemos nuestro "mini-Python" interno descargado.
3. Si no lo tenemos, el `run.bat` usa herramientas que ya vienen en Windows (PowerShell) para descargar silenciosamente una versión **Python 3.11 oficial y portable**.
4. Se extrae en una carpeta oculta dentro de la app llamada `.python_env`.
5. Se instala `pip` automáticamente dentro de ese entorno.
6. A partir de ese momento, la app usa **ese** Python específico (donde sabemos que los módulos de IA se instalan perfecto) e ignora cualquier otra versión que la computadora pueda tener instalada (como Python 3.14).

Esto convierte a MedicAItion en una aplicación **totalmente aislada y portátil**. Podrías llevártela en un disco duro externo y correría en otra computadora sin instalar nada extra.

## Modificaciones realizadas

### Modificación a `run.bat`
- Se eliminó la verificación global de `python`.
- Se añadieron comandos de PowerShell para descargar `python-3.11.9-embed-amd64.zip` si la carpeta `.python_env` no existe.
- Se extrae el ZIP y se borra el archivo original para ahorrar espacio.
- Se descarga e instala `pip` usando `get-pip.py`.
- Se modifica el archivo `python311._pth` para permitir la importación de `site-packages` (vital para instalar librerías de terceros).
- Finalmente, se ejecuta `run.py` usando exclusivamente el intérprete `.python_env\python.exe`.

## Proceso de Validación (Verificación)
1. Ejecutar `run.bat` desde la carpeta actual.
2. Observar en consola cómo descarga y extrae el entorno base (pasos 1/3, 2/3, 3/3).
3. Confirmar que el setup wizard se inicia correctamente y sin errores de sintaxis (dado que usa Python 3.11).
4. Completar el wizard y verificar que el modelo se descarga exitosamente.
