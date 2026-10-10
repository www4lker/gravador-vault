@echo off
REM Launcher Windows para scripts\transcrever-gradual.py. Uso: launchers\windows\transcrever-gradual.bat [argumentos]
call "%~dp0gv.bat" || exit /b 1
"%GV_PYTHON%" "%GV_RAIZ%\scripts\transcrever-gradual.py" %*
