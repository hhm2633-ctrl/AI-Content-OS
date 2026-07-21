@echo off
chcp 65001 >nul
title Seller Automation Server

echo ===================================================
echo   Seller Automation System - Windows 11
echo   This window keeps the server running.
echo   Do NOT close it while you are using the system.
echo ===================================================
echo.

REM ---- Find Python launcher: prefer py, then python ----
set "PYEXE="
where py >nul 2>&1
if %errorlevel%==0 set "PYEXE=py"
if not defined PYEXE (
  where python >nul 2>&1
  if %errorlevel%==0 set "PYEXE=python"
)

if not defined PYEXE goto NO_PYTHON

echo [OK] Using Python launcher: %PYEXE%
echo.

REM ---- Create virtual environment if missing ----
if exist "venv\Scripts\python.exe" goto HAVE_VENV
echo [INFO] Creating virtual environment venv ...
%PYEXE% -m venv venv
if errorlevel 1 goto VENV_FAIL

:HAVE_VENV
set "VENV_PY=venv\Scripts\python.exe"

REM ---- Install packages if FastAPI is missing ----
if exist "venv\Lib\site-packages\fastapi" goto RUN
echo [INFO] Installing required packages. Please wait 1-3 minutes ...
"%VENV_PY%" -m pip install --upgrade pip
"%VENV_PY%" -m pip install -r requirements.txt
if errorlevel 1 goto PIP_FAIL

:RUN
echo.
echo ===================================================
echo  Server starting ...
echo.
echo  On THIS PC, open a browser:  http://localhost:8000
echo  Default admin password:  admin1234
echo.
echo  On a phone/laptop in the same Wi-Fi:
echo      http://[this-PC-IP]:8000
echo      Example:  http://192.168.0.15:8000
echo  Then approve the new device from the Dashboard.
echo.
echo  To stop the server: close this window or press Ctrl+C.
echo ===================================================
echo.

"%VENV_PY%" -m uvicorn app.main:app --host 0.0.0.0 --port 8000

echo.
echo [INFO] Server stopped.
pause
exit /b 0

:NO_PYTHON
echo [ERROR] Python not found.
echo Install Python from https://www.python.org/downloads/
echo During install, CHECK "Add python.exe to PATH", then run again.
echo.
pause
exit /b 1

:VENV_FAIL
echo [ERROR] Failed to create virtual environment.
echo.
pause
exit /b 1

:PIP_FAIL
echo [ERROR] Package install failed. Check your internet connection.
echo.
pause
exit /b 1
