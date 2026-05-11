param(
  [string]$PythonExe = "python",
  [string]$ConfigPath = "config/config.yaml",
  [string]$EnvPath = ".env"
)

$ErrorActionPreference = "Stop"
Set-Location "$PSScriptRoot\.."

$cmd = "$PythonExe src/main.py --config $ConfigPath --env-file $EnvPath"

Write-Host "Executando: $cmd"
Invoke-Expression $cmd
