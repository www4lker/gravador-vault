@echo off
REM Launcher Windows para scripts\indexar.py. Uso: launchers\windows\indexar.bat [argumentos]
call "%~dp0gv.bat" || exit /b 1
"%GV_PYTHON%" "%GV_RAIZ%\scripts\indexar.py" %*
