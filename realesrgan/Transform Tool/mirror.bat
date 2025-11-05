@echo off
setlocal enableextensions

set "BASEDIR=%~dp0"
set "VENV=%BASEDIR%.venv"
set "PYTHON=%VENV%\Scripts\python.exe"
set "PYW=%VENV%\Scripts\pythonw.exe"

REM === 1) Comprobar que Python 3.10 existe en el sistema ===
py -3.10 -V >nul 2>&1
if errorlevel 1 (
  echo ==================================================
  echo  ERROR: Necesitas Python 3.10 x64 instalado.
  echo  El wheel FBX es cp310 y no sirve otra version.
  echo ==================================================
  pause
  exit /b 1
)

REM === 2) Si hay venv, comprobar su version; si no es 3.10, recrearlo ===
if exist "%PYTHON%" (
  for /f "usebackq delims=" %%A in (`"%PYTHON%" -c "import sys;print('%d.%d'%sys.version_info[:2])"`) do set "VENV_VER=%%A"
  if not "%VENV_VER%"=="3.10" (
    echo El venv actual usa Python %VENV_VER%. Lo recreo con 3.10...
    rmdir /s /q "%VENV%"
  )
)

REM === 3) Crear venv con Python 3.10 si no existe ===
if not exist "%PYTHON%" (
  echo Creando entorno virtual con Python 3.10...
  py -3.10 -m venv "%VENV%"
  if errorlevel 1 (
    echo Error creando venv con Python 3.10.
    pause
    exit /b 1
  )
)

REM === 4) Instalar dependencias ===
echo Instalando dependencias PyPI...
"%PYTHON%" -m pip install --upgrade pip
"%PYTHON%" -m pip install -r "%BASEDIR%requirements.txt"

echo Instalando FBX SDK wheel local...
"%PYTHON%" -m pip install --upgrade "%BASEDIR%dependencies\fbx-2020.3.4-cp310-none-win_amd64.whl"

REM === 5) Lanzar app (sin consola) ===
echo Lanzando combined_mirrorer.py...
start "" "%PYW%" "%BASEDIR%combined_mirrorer.py"

endlocal
