@echo off
setlocal
cd /d "%~dp0"
set "PY=D:\Users\Student\anaconda3\envs\yolov8\python.exe"
if exist "%PY%" (
  "%PY%" app.py
) else (
  python app.py
)
