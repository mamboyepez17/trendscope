@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\trendscope.exe" (
    echo No se encontró el entorno. Creando con uv...
    uv venv --python 3.11 .venv
    uv pip install -e .
)
.venv\Scripts\trendscope.exe
pause
