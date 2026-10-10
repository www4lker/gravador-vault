@echo off
REM Launcher Windows para scripts\organizar.py. Uso: launchers\windows\organizar.bat [argumentos]
call "%~dp0gv.bat" || exit /b 1
"%GV_PYTHON%" "%GV_RAIZ%\scripts\organizar.py" %*
