$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host 'Instale Node.js 22 ou superior em https://nodejs.org/ e tente novamente.'
    exit 1
}
node scripts/serve.mjs --open
