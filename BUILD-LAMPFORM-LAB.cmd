@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  if errorlevel 1 goto fail
)
".venv\Scripts\python.exe" -m pip install -r requirements-analysis.txt
if errorlevel 1 goto fail
call npm ci
if errorlevel 1 goto fail
".venv\Scripts\python.exe" analysis\build_design_space.py
if errorlevel 1 goto fail
".venv\Scripts\python.exe" analysis\build_physical.py
if errorlevel 1 goto fail
call npm run build
if errorlevel 1 goto fail
call npm test
if errorlevel 1 goto fail
echo Build complete. Run PLAY-LAMPFORM-LAB.cmd to open the local workbench.
exit /b 0
:fail
echo Build failed. Review the error above. Requires Python 3.13+ and Node.js 22+.
exit /b 1
