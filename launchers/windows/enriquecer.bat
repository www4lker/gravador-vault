@echo off
REM Launcher Windows para scripts\enriquecer.py. Uso: launchers\windows\enriquecer.bat [argumentos]
call "%~dp0gv.bat" || exit /b 1
"%GV_PYTHON%" "%GV_RAIZ%\scripts\enriquecer.py" %*
