@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo Cai dat that bai. Hay kiem tra Python va ket noi Internet.
    pause
    exit /b 1
)
echo Cai dat xong. Mo RUN_TOOL.bat de chay.
pause
