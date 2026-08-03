# Arranque automático del asistente (que trabaje solo)

Estos archivos dejan el asistente corriendo **solo**, cada X minutos, arrancando
al encender la máquina. Elegí tu sistema operativo.

> 🔴 **Requisito común (no negociable):** todo esto corre en la **máquina donde
> tenés el navegador logueado** en IG/TikTok/FB, con Chrome abierto y la extensión
> **Browser MCP en Connect**. Antes de instalar el servicio, dejá una vez el repo
> compilado (`npm install && npm run build`) y probá una ronda a mano:
> `docs/asistente-mood-mayorista/run-round.sh`.

---

## Linux (systemd, sesión de escritorio)

```bash
cp deploy/systemd/mood-asistente.service ~/.config/systemd/user/
# editá REPO/PATH dentro del archivo si hace falta
systemctl --user daemon-reload
systemctl --user enable --now mood-asistente.service
loginctl enable-linger "$USER"        # opcional: corre sin login
journalctl --user -u mood-asistente -f   # ver logs
```

## macOS (launchd)

```bash
# reemplazá TU_USUARIO en el .plist, luego:
cp deploy/launchd/com.moodmayorista.asistente.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.moodmayorista.asistente.plist
# detener: launchctl unload ~/Library/LaunchAgents/com.moodmayorista.asistente.plist
```

## Windows (Tarea Programada, con Git Bash o WSL)

```powershell
cd docs\asistente-mood-mayorista\deploy\windows
./Install-MoodAsistente.ps1 -RepoDir "C:\ruta\a\browsermcp-mcp" -IntervalMinutes 10
# desinstalar: Unregister-ScheduledTask -TaskName "MoodMayorista-Asistente" -Confirm:$false
```

---

## ¿Y una "Rutina" de Claude en la nube?

No sirve para esto. Una Routine/tarea programada que se ejecuta en la nube **no
tiene acceso a tu navegador ni a tus sesiones** de IG/TikTok/FB (Browser MCP es
local). Solo la rutina **local** (los servicios de arriba) puede leer y contestar
en tus redes. El texto que dispara cada ronda está en `../rutina-prompt.txt`.

## Verificación

- El servicio quedó activo (`systemctl --user status …` / `launchctl list | grep mood` /
  Task Scheduler → "MoodMayorista-Asistente").
- Aparecen logs en `docs/asistente-mood-mayorista/logs/ronda-*.log`.
- La primera ronda supervisada hace lo esperado (leer pendientes, contestar,
  cierre de turno). **Mirá las primeras rondas a mano** antes de dejarlo solo.
