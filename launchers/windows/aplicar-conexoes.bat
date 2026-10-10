@echo off
REM Launcher Windows para scripts\aplicar-conexoes.py. Uso: launchers\windows\aplicar-conexoes.bat [argumentos]
call "%~dp0gv.bat" || exit /b 1
"%GV_PYTHON%" "%GV_RAIZ%\scripts\aplicar-conexoes.py" %*
