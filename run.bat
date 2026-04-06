@echo off
:: ============================================================
:: run.bat — Start the entire DFS on Windows
:: Usage:  run.bat [stop]
:: ============================================================

set ROOT=%~dp0
cd /d "%ROOT%"

if "%1"=="stop" goto :stop

:start
echo ==============================
echo   Distributed File System
echo ==============================

if not exist logs         mkdir logs
if not exist nodes\storage\node1 mkdir nodes\storage\node1
if not exist nodes\storage\node2 mkdir nodes\storage\node2
if not exist nodes\storage\node3 mkdir nodes\storage\node3
if not exist downloads    mkdir downloads

echo [1/4] Starting master...
start "DFS-Master" /MIN python -m master.master

timeout /t 1 /nobreak >nul

echo [2/4] Starting node 1...
set NODE_ID=1
start "DFS-Node1" /MIN python -m nodes.node

echo [3/4] Starting node 2...
set NODE_ID=2
start "DFS-Node2" /MIN python -m nodes.node

echo [4/4] Starting node 3...
set NODE_ID=3
start "DFS-Node3" /MIN python -m nodes.node

echo.
echo All processes started in background windows.
echo.
echo Client commands:
echo   python -m client.client upload   ^<file^>
echo   python -m client.client download ^<file^>
echo   python -m client.client list
echo.
goto :eof

:stop
echo Stopping DFS (closing titled windows)...
taskkill /FI "WINDOWTITLE eq DFS-Master" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq DFS-Node1"  /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq DFS-Node2"  /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq DFS-Node3"  /F >nul 2>&1
echo Done.
