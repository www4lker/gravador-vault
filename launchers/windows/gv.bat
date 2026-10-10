@echo off
REM Bootstrap do ambiente gravador-vault no Windows.
REM Chamado pelos outros .bat com: call "%~dp0gv.bat"
REM Le o .env da raiz do repositorio (KEY=VALUE) sem sobrescrever variaveis ja definidas.

set "GV_RAIZ=%~dp0..\.."
for %%I in ("%GV_RAIZ%") do set "GV_RAIZ=%%~fI"

if exist "%GV_RAIZ%\.env" (
  for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%GV_RAIZ%\.env") do (
    if not defined %%A set "%%A=%%B"
  )
)

if not defined PYTHONUTF8 set PYTHONUTF8=1

set "GV_PYTHON=%GV_RAIZ%\.venv\Scripts\python.exe"
if not exist "%GV_PYTHON%" (
  where python >nul 2>&1
  if errorlevel 1 (
    echo Erro: Python nao encontrado. Rode launchers\windows\instalar.bat primeiro.
    exit /b 1
  )
  set "GV_PYTHON=python"
)
