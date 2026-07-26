@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo No se encontró .venv. Creando entorno con uv...
    uv venv --python 3.11 .venv
    uv pip install -e ".[dev]"
)
.venv\Scripts\python.exe -m pytest trendscope/tests/ -v
pause
