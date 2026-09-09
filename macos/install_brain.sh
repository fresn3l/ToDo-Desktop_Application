#!/usr/bin/env bash
# Install Ollama + Cluny on this Mac into a path Kosistenz already searches.
# Cluny indexes journals, work, clock, workouts, and goals. It does not schedule.
# Kosistenz stays a separate process and stays usable if Cluny is quit.
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This installer is for macOS. Run it on your Mac." >&2
  echo "Ollama and Cluny stay on-device; this Linux environment cannot install them onto your Mac." >&2
  exit 1
fi

export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/local/sbin:${PATH:-/usr/bin:/bin}"

CLUNY_REPO_URL="${CLUNY_REPO_URL:-https://github.com/fresn3l/Cluny_the_AI_Agent.git}"
CLUNY_ROOT="${CLUNY_DATA_DIR:-$HOME/Library/Application Support/Cluny}"
CLUNY_SRC="${CLUNY_SRC:-$CLUNY_ROOT/src}"
CLUNY_BIN_DIR="$CLUNY_ROOT/bin"
CLUNY_WRAPPER="$CLUNY_BIN_DIR/cluny"
CLUNY_VENV_BIN="$CLUNY_SRC/.venv/bin/cluny"
TODO_DIR="${KOSISTENZ_DATA_DIR:-$HOME/Library/Application Support/ToDo}"
CHAT_MODEL="${CLUNY_OLLAMA_CHAT_MODEL:-llama3.2}"
EMBED_MODEL="${CLUNY_OLLAMA_EMBED_MODEL:-nomic-embed-text}"

mkdir -p "$CLUNY_ROOT" "$CLUNY_BIN_DIR" "$TODO_DIR"

python_is_311() {
  local bin="$1"
  if [[ ! -x "$bin" ]] && ! command -v "$bin" >/dev/null 2>&1; then
    return 1
  fi
  "$bin" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null
}

resolve_python() {
  local bin="$1"
  local found
  found="$(command -v "$bin" 2>/dev/null || true)"
  if [[ -n "$found" ]]; then
    echo "$found"
    return 0
  fi
  if [[ -x "$bin" ]]; then
    echo "$bin"
    return 0
  fi
  return 1
}

find_python() {
  local cand resolved
  local candidates=()
  if [[ -n "${PYTHON:-}" ]]; then
    candidates+=("$PYTHON")
  fi
  candidates+=(
    python3.13 python3.12 python3.11
    /opt/homebrew/bin/python3.13 /opt/homebrew/bin/python3.12 /opt/homebrew/bin/python3.11
    /usr/local/bin/python3.13 /usr/local/bin/python3.12 /usr/local/bin/python3.11
    python3
  )
  for cand in "${candidates[@]}"; do
    [[ -z "$cand" ]] && continue
    if ! python_is_311 "$cand"; then
      continue
    fi
    resolved="$(resolve_python "$cand" || true)"
    if [[ -n "$resolved" ]]; then
      echo "$resolved"
      return 0
    fi
  done
  return 1
}

need_git() {
  if command -v git >/dev/null 2>&1; then
    return 0
  fi
  echo "Need git on PATH to clone Cluny." >&2
  echo "Install Xcode Command Line Tools: xcode-select --install" >&2
  exit 1
}

install_python_if_needed() {
  if PY="$(find_python)"; then
    echo "Using Python: $PY ($("$PY" -c 'import sys; print("%d.%d"%sys.version_info[:2])'))"
    return 0
  fi
  if command -v brew >/dev/null 2>&1; then
    echo "Cluny needs Python 3.11+. Installing python@3.12 with Homebrew…"
    brew install python@3.12
  fi
  if PY="$(find_python)"; then
    echo "Using Python: $PY"
    return 0
  fi
  echo "Need Python 3.11+ for Cluny (found none)." >&2
  echo "Install Python 3.12 from https://www.python.org/downloads/macos/ or: brew install python@3.12" >&2
  exit 1
}

find_ollama() {
  local p
  if command -v ollama >/dev/null 2>&1; then
    command -v ollama
    return 0
  fi
  for p in \
    /opt/homebrew/bin/ollama \
    /usr/local/bin/ollama \
    /Applications/Ollama.app/Contents/Resources/ollama \
    "$HOME/Applications/Ollama.app/Contents/Resources/ollama"
  do
    if [[ -x "$p" ]]; then
      echo "$p"
      return 0
    fi
  done
  return 1
}

ollama_ready() {
  curl -sf http://127.0.0.1:11434/api/tags >/dev/null 2>&1
}

copy_ollama_app() {
  local src="$1"
  local dest
  if [[ -w /Applications ]]; then
    dest="/Applications/Ollama.app"
    rm -rf "$dest"
    cp -R "$src" "$dest"
    xattr -dr com.apple.quarantine "$dest" 2>/dev/null || true
    echo "$dest"
    return 0
  fi
  mkdir -p "$HOME/Applications"
  dest="$HOME/Applications/Ollama.app"
  rm -rf "$dest"
  cp -R "$src" "$dest"
  xattr -dr com.apple.quarantine "$dest" 2>/dev/null || true
  echo "$dest"
}

install_ollama() {
  if OLLAMA_BIN="$(find_ollama)"; then
    echo "Ollama already installed: $OLLAMA_BIN"
    return 0
  fi

  echo "Installing Ollama (on-device; no cloud LLM)…"
  if command -v brew >/dev/null 2>&1; then
    if brew install ollama; then
      if OLLAMA_BIN="$(find_ollama)"; then
        echo "Ollama installed with Homebrew: $OLLAMA_BIN"
        return 0
      fi
    else
      echo "Homebrew Ollama formula failed; trying the Mac app download…"
    fi
    if brew install --cask ollama 2>/dev/null || brew install --cask ollama-app 2>/dev/null; then
      if OLLAMA_BIN="$(find_ollama)"; then
        echo "Ollama app installed with Homebrew: $OLLAMA_BIN"
        return 0
      fi
    fi
  fi

  local tmp zip app
  tmp="$(mktemp -d)"
  zip="$tmp/Ollama-darwin.zip"
  echo "Downloading Ollama for Mac from https://ollama.com/download/Ollama-darwin.zip"
  if ! curl -fL --retry 3 --retry-delay 2 -o "$zip" "https://ollama.com/download/Ollama-darwin.zip"; then
    echo "Could not download Ollama." >&2
    echo "Install it from https://ollama.com/download then re-run ./macos/install_brain.sh" >&2
    rm -rf "$tmp"
    exit 1
  fi
  unzip -q "$zip" -d "$tmp"
  app="$(find "$tmp" -name "Ollama.app" -type d -print -quit || true)"
  if [[ -z "$app" || ! -d "$app" ]]; then
    echo "Downloaded Ollama zip but Ollama.app was not inside it." >&2
    echo "Install it from https://ollama.com/download then re-run ./macos/install_brain.sh" >&2
    rm -rf "$tmp"
    exit 1
  fi
  copy_ollama_app "$app" >/dev/null
  rm -rf "$tmp"
  if ! OLLAMA_BIN="$(find_ollama)"; then
    echo "Ollama.app was copied but the ollama binary was not found." >&2
    echo "Open Ollama once from Applications, then re-run ./macos/install_brain.sh" >&2
    exit 1
  fi
  echo "Ollama installed: $OLLAMA_BIN"
}

start_ollama() {
  if ollama_ready; then
    echo "Ollama is already running."
    return 0
  fi
  echo "Starting Ollama…"
  if [[ -d /Applications/Ollama.app ]]; then
    open -a Ollama || true
  elif [[ -d "$HOME/Applications/Ollama.app" ]]; then
    open -a "$HOME/Applications/Ollama.app" || true
  fi
  if ! ollama_ready; then
    nohup "$OLLAMA_BIN" serve >/tmp/kosistenz-ollama-serve.log 2>&1 &
  fi
  local i
  for i in $(seq 1 60); do
    if ollama_ready; then
      echo "Ollama is ready."
      return 0
    fi
    sleep 1
  done
  echo "Ollama did not become ready on http://127.0.0.1:11434." >&2
  echo "Open Ollama.app once, wait until it is running, then re-run ./macos/install_brain.sh" >&2
  if [[ -f /tmp/kosistenz-ollama-serve.log ]]; then
    echo "Log: /tmp/kosistenz-ollama-serve.log" >&2
  fi
  exit 1
}

pull_models() {
  if [[ "${SKIP_MODELS:-0}" == "1" ]]; then
    echo "Skipping model pull (SKIP_MODELS=1)."
    return 0
  fi
  echo "Pulling Ollama models ${CHAT_MODEL} and ${EMBED_MODEL} (this can take a while)…"
  "$OLLAMA_BIN" pull "$CHAT_MODEL"
  "$OLLAMA_BIN" pull "$EMBED_MODEL"
}

clone_cluny() {
  need_git
  if [[ -d "$CLUNY_SRC/.git" ]]; then
    echo "Cluny source already present: $CLUNY_SRC"
    if [[ "${SKIP_PULL:-0}" == "1" ]]; then
      return 0
    fi
    if git -C "$CLUNY_SRC" pull --ff-only; then
      echo "Updated Cluny source."
    else
      echo "Could not fast-forward $CLUNY_SRC; leaving the existing checkout."
    fi
    return 0
  fi
  if [[ -e "$CLUNY_SRC" && ! -d "$CLUNY_SRC/.git" ]]; then
    echo "$CLUNY_SRC exists but is not a git checkout. Move it aside and re-run." >&2
    exit 1
  fi
  echo "Cloning $CLUNY_REPO_URL into $CLUNY_SRC"
  git clone "$CLUNY_REPO_URL" "$CLUNY_SRC"
}

install_cluny_venv() {
  echo "Installing Cluny into a venv (editable + API extras for cluny serve)…"
  cd "$CLUNY_SRC"
  if [[ ! -d .venv ]]; then
    "$PY" -m venv .venv
  fi
  ./.venv/bin/python -m pip install -U pip
  ./.venv/bin/python -m pip install -e ".[api]"
  if [[ ! -x "$CLUNY_VENV_BIN" ]]; then
    echo "pip install finished but $CLUNY_VENV_BIN is not executable." >&2
    exit 1
  fi
}

write_wrapper() {
  cat > "$CLUNY_WRAPPER" <<EOF
#!/bin/bash
# Kosistenz-installed Cluny. Keeps CLUNY_DATA_DIR on Application Support/Cluny.
set -euo pipefail
export CLUNY_DATA_DIR="\${CLUNY_DATA_DIR:-$CLUNY_ROOT}"
CLUNY_BIN="$CLUNY_VENV_BIN"
if [[ ! -x "\$CLUNY_BIN" ]]; then
  echo "Cluny venv binary missing: \$CLUNY_BIN" >&2
  echo "Re-run: ./macos/install_brain.sh" >&2
  exit 1
fi
exec "\$CLUNY_BIN" "\$@"
EOF
  chmod +x "$CLUNY_WRAPPER"
  echo "Wrote Cluny wrapper: $CLUNY_WRAPPER"
}

write_kosistenz_settings() {
  "$PY" - "$TODO_DIR" "$CLUNY_WRAPPER" "$CLUNY_ROOT" <<'PY'
import json
import sys
from pathlib import Path

todo_dir = Path(sys.argv[1])
binary = sys.argv[2]
data_dir = sys.argv[3]
todo_dir.mkdir(parents=True, exist_ok=True)
path = todo_dir / "cluny_settings.json"
data = {}
if path.exists():
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            data = loaded
    except (OSError, json.JSONDecodeError):
        data = {}
data["cluny_binary_path"] = binary
data["cluny_data_dir"] = data_dir
if "auto_start_brain" not in data:
    data["auto_start_brain"] = True
tmp = path.with_suffix(".json.tmp")
tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
tmp.replace(path)
print(f"Wrote Kosistenz settings: {path}")
PY
}

echo "Installing Cluny + Ollama for Kosistenz."
echo "Cluny is the local brain. Kosistenz stays the planner (one clock, one to-do list)."
echo ""

install_python_if_needed
install_ollama
start_ollama
pull_models
clone_cluny
install_cluny_venv
write_wrapper
write_kosistenz_settings

echo ""
echo "Done. Cluny binary: $CLUNY_WRAPPER"
echo "Cluny data:        $CLUNY_ROOT"
echo "Ollama models:     $CHAT_MODEL, $EMBED_MODEL"
echo ""
echo "Next:"
echo "  Open Kosistenz → Settings → Cluny → Test connection"
echo "  Then Index my life"
echo "Kosistenz still works if you quit Cluny. The iPhone does not run Ask Cluny."
echo "Serve log once the app starts him: ~/Library/Logs/Kosistenz-cluny-serve.log"
