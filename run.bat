@echo off
title MedicAItion — Cruz Roja Merida
color 0A

echo.
echo  ============================================
echo   MedicAItion ^|^| Cruz Roja Merida
echo  ============================================
echo.

set ENV_DIR=.python_env
set PY_VER=3.11.9
set PY_ZIP=python-%PY_VER%-embed-amd64.zip
set PY_URL=https://www.python.org/ftp/python/%PY_VER%/%PY_ZIP%

if not exist "%ENV_DIR%\python.exe" (
    echo  [!] Configurando entorno autonomo ^(Python %PY_VER% Portable^)...
    echo      Esto solo se hara la primera vez. Puede tardar un par de minutos.
    echo.
    
    if not exist "%ENV_DIR%" mkdir "%ENV_DIR%"
    
    echo  1/3 Descargando entorno base...
    powershell -Command "Invoke-WebRequest -Uri '%PY_URL%' -OutFile '%PY_ZIP%'"
    
    echo  2/3 Extrayendo archivos...
    powershell -Command "Expand-Archive -Path '%PY_ZIP%' -DestinationPath '%ENV_DIR%' -Force"
    del "%PY_ZIP%"
    
    echo  3/3 Configurando el instalador de paquetes...
    powershell -Command "Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%ENV_DIR%\get-pip.py'"
    
    :: Descomentar import site en el archivo _pth para habilitar pip
    powershell -Command "(Get-Content '%ENV_DIR%\python311._pth') -replace '#import site', 'import site' | Set-Content '%ENV_DIR%\python311._pth'"
    
    "%ENV_DIR%\python.exe" "%ENV_DIR%\get-pip.py" >nul 2>&1
    del "%ENV_DIR%\get-pip.py"
    
    echo.
    echo  [OK] Entorno autonomo listo.
    echo.
)

echo  Iniciando MedicAItion...
echo.

:: Inyectar librerias CUDA portatiles al PATH (necesarias para GPU)
set "CUDA_RT=%CD%\%ENV_DIR%\Lib\site-packages\nvidia\cuda_runtime\bin"
set "CUDA_BLAS=%CD%\%ENV_DIR%\Lib\site-packages\nvidia\cublas\bin"
if exist "%CUDA_RT%" set "PATH=%CUDA_RT%;%PATH%"
if exist "%CUDA_BLAS%" set "PATH=%CUDA_BLAS%;%PATH%"

"%ENV_DIR%\python.exe" run.py

if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] Ocurrio un error. Revisa los mensajes anteriores.
    pause
)
