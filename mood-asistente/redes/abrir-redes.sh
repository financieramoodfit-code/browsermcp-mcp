#!/bin/bash
#
# Abre en Chrome, de una, todas las pestañas que necesita el asistente de
# Mood Mayorista (macOS y Linux). Para Windows: abrir-redes.ps1
#
# Chrome no permite crear un GRUPO de pestañas por línea de comandos. Este
# script abre las 8 pestañas; para dejarlas agrupadas y con nombre, hacé una
# sola vez lo de REDES-SOCIALES.html (ver README.md de esta carpeta).
#
set -euo pipefail

URLS=(
  "https://www.instagram.com/direct/inbox/"
  "https://www.instagram.com/moodfitmayorista/"
  "https://www.tiktok.com/messages"
  "https://www.tiktok.com/@moodfitmayorista"
  "https://business.facebook.com/latest/inbox/all"
  "https://www.facebook.com/MoodFitOficial"
  "https://web.whatsapp.com/"
  "https://docs.google.com/spreadsheets/d/1ixzRKmmfRSi2fR1gp-XVCYrT-414hDjuhHu0RSDtQTo/edit?gid=1432692705#gid=1432692705"
)

if [ "$(uname -s)" = "Darwin" ]; then
  open -a "Google Chrome" "${URLS[@]}"
  echo "Listo: 8 pestañas abiertas en Chrome."
  exit 0
fi

for candidate in google-chrome google-chrome-stable chromium chromium-browser; do
  if command -v "$candidate" >/dev/null 2>&1; then
    "$candidate" "${URLS[@]}" >/dev/null 2>&1 &
    echo "Listo: 8 pestañas abiertas en $candidate."
    exit 0
  fi
done

echo "No encontré Chrome en el PATH." >&2
echo "Instalalo, o abrí a mano las URLs que están en REDES-SOCIALES.html." >&2
exit 1
