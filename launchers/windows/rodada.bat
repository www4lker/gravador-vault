@echo off
REM Launcher Windows para scripts\rodada.py. Uso: launchers\windows\rodada.bat [argumentos]
call "%~dp0gv.bat" || exit /b 1
"%GV_PYTHON%" "%GV_RAIZ%\scripts\rodada.py" %*
