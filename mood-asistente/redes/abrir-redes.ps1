<#
  Abre en Chrome, de una, todas las pestañas que necesita el asistente de
  Mood Mayorista (Windows).

  Uso:  powershell -ExecutionPolicy Bypass -File abrir-redes.ps1

  Chrome no permite crear un GRUPO de pestañas por línea de comandos. Este
  script abre las 8 pestañas; para dejarlas agrupadas y con nombre, hacé una
  sola vez lo de REDES-SOCIALES.html (ver README.md de esta carpeta).
#>

$urls = @(
  "https://www.instagram.com/direct/inbox/",
  "https://www.instagram.com/moodfitmayorista/",
  "https://www.tiktok.com/messages",
  "https://www.tiktok.com/@moodfitmayorista",
  "https://business.facebook.com/latest/inbox/all",
  "https://www.facebook.com/MoodFitOficial",
  "https://web.whatsapp.com/",
  "https://docs.google.com/spreadsheets/d/1ixzRKmmfRSi2fR1gp-XVCYrT-414hDjuhHu0RSDtQTo/edit?gid=1432692705#gid=1432692705"
)

$candidatos = @(
  "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
  "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
  "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
)

$chrome = $candidatos | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $chrome) {
  Write-Error "No encontré chrome.exe. Abrí a mano las URLs de REDES-SOCIALES.html."
  exit 1
}

& $chrome $urls
Write-Host "Listo: 8 pestañas abiertas en Chrome."
