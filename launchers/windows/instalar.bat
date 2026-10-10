@echo off
setlocal
REM instalar.bat — cria o venv do repositorio (.venv\) e instala as dependencias.
REM Nao grava nada fora da pasta do repositorio. ffmpeg precisa ser instalado a parte.

set "GV_RAIZ=%~dp0..\.."
for %%I in ("%GV_RAIZ%") do set "GV_RAIZ=%%~fI"

echo === gravador-vault: instalacao do ambiente ===
echo Raiz: %GV_RAIZ%
echo.

where python >nul 2>&1
if errorlevel 1 (
  echo Erro: Python nao encontrado no PATH. Instale Python 3.10+ (python.org) marcando "Add to PATH".
  pause
  exit /b 1
)

if not exist "%GV_RAIZ%\.venv\Scripts\python.exe" (
  echo [1/3] Criando venv em %GV_RAIZ%\.venv ...
  python -m venv "%GV_RAIZ%\.venv" || exit /b 1
) else (
  echo [1/3] venv ja existe.
)

echo [2/3] Instalando dependencias ...
"%GV_RAIZ%\.venv\Scripts\python.exe" -m pip install --upgrade pip >nul
"%GV_RAIZ%\.venv\Scripts\python.exe" -m pip install -r "%GV_RAIZ%\requirements.txt" || exit /b 1

echo [3/3] Configuracao
if not exist "%GV_RAIZ%\.env" (
  copy "%GV_RAIZ%\.env.example" "%GV_RAIZ%\.env" >nul
  echo Criado %GV_RAIZ%\.env a partir do exemplo. EDITE-O e defina GV_VAULT.
) else (
  echo .env ja existe.
)

echo.
echo === Falta so o ffmpeg ===
echo  1. Baixe uma build "essentials" de https://www.gyan.dev/ffmpeg/builds/
echo  2. Extraia e adicione a pasta bin\ ao PATH do usuario
echo  3. Confira com: ffmpeg -version
echo.
echo Teste: launchers\windows\transcrever.bat --dry-run
endlocal
pause
