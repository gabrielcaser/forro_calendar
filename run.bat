@echo off
REM Script executado pelo Windows Task Scheduler toda terça às 8h
cd /d "%~dp0"

REM Executa o script principal usando o Python do ambiente virtual
"%~dp0venv\Scripts\python.exe" "%~dp0main.py"
