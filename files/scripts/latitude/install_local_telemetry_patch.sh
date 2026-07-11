#!/usr/bin/env bash
set -euo pipefail

VENV_PY="/usr/local/lib/hermes-agent/venv/bin/python"
PKG_DIR="/root/.hermes/local-packages/latitude-telemetry-hermes"
VALIDATE="/root/.hermes/scripts/latitude/dewey_observability_validate.py"
CORE_LOOP="/usr/local/lib/hermes-agent/agent/conversation_loop.py"

if [[ ! -x "$VENV_PY" ]]; then
  echo "Hermes venv Python not found: $VENV_PY" >&2
  exit 1
fi
if [[ ! -f "$PKG_DIR/pyproject.toml" ]]; then
  echo "Local telemetry package not found: $PKG_DIR" >&2
  exit 1
fi

# The plugin needs Hermes' live, per-call reasoning_config in the sanitized
# pre_api_request hook. Reapply this tiny core hook addition after Hermes
# upgrades so session /reasoning overrides remain observable.
"$VENV_PY" - "$CORE_LOOP" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
needle = "                            reasoning_config=agent.reasoning_config,\n"
if needle not in text:
    anchor = (
        "                            max_tokens=agent.max_tokens,\n"
        "                            started_at=api_start_time,\n"
    )
    replacement = (
        "                            max_tokens=agent.max_tokens,\n"
        "                            reasoning_config=agent.reasoning_config,\n"
        "                            started_at=api_start_time,\n"
    )
    if anchor not in text:
        raise SystemExit(f"Hermes pre_api_request hook anchor not found: {path}")
    path.write_text(text.replace(anchor, replacement, 1), encoding="utf-8")
    print("Patched Hermes pre_api_request reasoning_config hook")
else:
    print("Hermes pre_api_request reasoning_config hook already present")
PY

# The Hermes venv is uv-managed and may ship no pip — fall back to uv.
"$VENV_PY" -m pip install -e "$PKG_DIR" \
  || uv pip install --python "$VENV_PY" -e "$PKG_DIR" \
  || /root/.hermes/bin/uv pip install --python "$VENV_PY" -e "$PKG_DIR"
"$VENV_PY" - <<'PY'
import importlib.metadata as md
import pathlib
import latitude_telemetry_hermes
print('latitude-telemetry-hermes', md.version('latitude-telemetry-hermes'))
print('module_file', pathlib.Path(latitude_telemetry_hermes.__file__).resolve())
PY

if [[ -f "$VALIDATE" ]]; then
  python3 "$VALIDATE"
fi
