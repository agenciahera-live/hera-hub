@echo off
REM Liga o Hera Creator Hub no seu computador. Feche esta janela para desligar.
cd /d "%~dp0"
start "" http://localhost:8000
".venv\Scripts\python.exe" manage.py runserver 8000
pause
