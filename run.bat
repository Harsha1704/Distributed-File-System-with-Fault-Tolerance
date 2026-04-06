@echo off
:: ============================================================
:: run.bat — Start/Stop Distributed File System (Windows)
:: ============================================================

set ROOT=%~dp0
cd /d "%ROOT%"

if "%1"=="stop" goto :stop

:start
echo ==============================
echo   Distributed File System
echo ==============================

:: Create required folders
if not exist logs mkdir logs
if not exist nodes\storage\node1 mkdir nodes\storage\node1
if not exist nodes\storage\node2 mkdir nodes\storage\node2
if not exist nodes\storage\node3 mkdir nodes\storage\node3
if not exist downloads mkdir downloads

echo [1/5] Starting master...
start "DFS-Master" cmd /k "python -m master.master"

ping 127.0.0.1 -n 3 > nul

echo [2/5] Starting node 1...
start "DFS-Node1" cmd /k "set NODE_ID=1 && python -m nodes.node"

echo [3/5] Starting node 2...
start "DFS-Node2" cmd /k "set NODE_ID=2 && python -m nodes.node"

echo [4/5] Starting node 3...
start "DFS-Node3" cmd /k "set NODE_ID=3 && python -m nodes.node"

ping 127.0.0.1 -n 3 > nul

echo [5/5] Starting GUI...
@REM start "DFS-GUI" cmd /k "cd gui && python main_gui.py"
start "DFS-GUI" cmd /k "set PYTHONPATH=%ROOT% && python -m gui.main_gui"
echo.
echo ✅ System + GUI started
echo.
goto :eof


:stop
echo Stopping DFS (closing all windows)...
taskkill /FI "WINDOWTITLE eq DFS-Master*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq DFS-Node1*"  /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq DFS-Node2*"  /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq DFS-Node3*"  /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq DFS-GUI*"    /F >nul 2>&1
echo Done.