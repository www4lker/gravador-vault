@echo off
REM Launcher Windows para scripts\conectar.py. Uso: launchers\windows\conectar.bat [argumentos]
call "%~dp0gv.bat" || exit /b 1
"%GV_PYTHON%" "%GV_RAIZ%\scripts\conectar.py" %*
