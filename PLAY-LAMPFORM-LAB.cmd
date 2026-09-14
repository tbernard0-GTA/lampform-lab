@echo off
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo Instale Node.js 22 ou superior em https://nodejs.org/ e tente novamente.
  pause
  exit /b 1
)
node scripts/serve.mjs --open
pause
