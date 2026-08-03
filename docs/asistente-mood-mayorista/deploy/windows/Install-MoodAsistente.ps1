<#
  Instalador de la tarea programada (Windows) — Asistente Virtual Mood Mayorista.

  Registra una Tarea Programada que ejecuta run-round.sh cada N minutos usando
  el bash de Git for Windows (o WSL). Requiere Chrome abierto + extensión
  Browser MCP en Connect en esta PC, y el CLI `claude` + `node` disponibles.

  Uso (PowerShell, como tu usuario):
    ./Install-MoodAsistente.ps1 -RepoDir "C:\ruta\a\browsermcp-mcp" -IntervalMinutes 10

  Parametros:
    -RepoDir          Ruta del repo browsermcp-mcp (obligatorio).
    -IntervalMinutes  Cada cuantos minutos corre (default 10).
    -BashExe          Ruta a bash.exe (default: Git Bash en Program Files).

  Para desinstalar:
    Unregister-ScheduledTask -TaskName "MoodMayorista-Asistente" -Confirm:$false

  Logs: en <RepoDir>\docs\asistente-mood-mayorista\logs\
#>
param(
  [Parameter(Mandatory = $true)] [string] $RepoDir,
  [int] $IntervalMinutes = 10,
  [string] $BashExe = "C:\Program Files\Git\bin\bash.exe"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $BashExe)) {
  throw "No se encontro bash en '$BashExe'. Instala Git for Windows o pasa -BashExe con la ruta correcta (o el bash de WSL)."
}

$roundScript = Join-Path $RepoDir "docs\asistente-mood-mayorista\run-round.sh"
if (-not (Test-Path $roundScript)) {
  throw "No se encontro run-round.sh en '$roundScript'. Verifica -RepoDir."
}

# bash necesita la ruta en formato POSIX (/c/...). Convertimos C:\... -> /c/...
$posix = "/" + ($roundScript -replace ":", "" -replace "\\", "/")
$posix = $posix.Substring(0,2).ToLower() + $posix.Substring(2)

$taskName = "MoodMayorista-Asistente"
$action   = New-ScheduledTaskAction -Execute $BashExe -Argument "-lc `"$posix`""

# Dispara al iniciar sesion y luego se repite cada N minutos, indefinidamente.
$trigger = New-ScheduledTaskTrigger -AtLogOn
$trigger.Repetition = (New-ScheduledTaskTrigger -Once -At (Get-Date) `
  -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
  -RepetitionDuration ([TimeSpan]::MaxValue)).Repetition

$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries `
  -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
  -Settings $settings -Description "Asistente Virtual Mood Mayorista (Browser MCP)" -Force

Write-Host "Tarea '$taskName' registrada: corre cada $IntervalMinutes min." -ForegroundColor Green
Write-Host "Recorda tener Chrome abierto y la extension Browser MCP en Connect." -ForegroundColor Yellow
