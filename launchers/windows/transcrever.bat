@echo off
REM Launcher Windows para scripts\transcrever.py. Uso: launchers\windows\transcrever.bat [argumentos]
call "%~dp0gv.bat" || exit /b 1
"%GV_PYTHON%" "%GV_RAIZ%\scripts\transcrever.py" %*
