# cc-bridge — puntea Claude Code ↔ Hermes

Piesele: `cc-bridge` (CLI: administrarea sesiunilor CC — citire transcript
JSONL + hooks, scriere tmux) și `cc-mirror-shim` (server OpenAI-compatible pe
:9127 — o sesiune Hermes devine o conversație CC; config per sesiune în
SESSION_PROFILES).

Deploy: `~/.local/bin/{cc-bridge,cc-mirror-shim}` sunt symlink-uri către acest
repo. Shim-ul rulează ca systemd user unit `cc-mirror-shim.service` (copie în
repo). După orice modificare: commit aici + `systemctl --user restart
cc-mirror-shim`.
