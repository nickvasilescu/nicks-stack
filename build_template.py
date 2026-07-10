#!/usr/bin/env python3
# ==========================================================================
# Nick's Stack — template builder / publisher  (key-less, self-contained)
# ==========================================================================
# Assembles the orgo.ai/v1 template dict programmatically from the byte-exact
# files in ./files, validates it against the schema, and (optionally) runs the
# proven publish -> build -> stream -> launch REST flow.
#
#   python3 build_template.py                 # assemble + local jsonschema validate + dump resolved.json
#   python3 build_template.py --remote-validate   # + POST /api/templates/validate
#   python3 build_template.py --publish       # publish (wrapped envelope)
#   python3 build_template.py --build         # publish + trigger build + stream events to ready
#   python3 build_template.py --launch WS_ID  # + launch a test VM into that workspace
#   VERSION=0.1.2 python3 build_template.py --build   # bump the patch each rebuild
#
# NO SECRETS are baked. The template declares the secrets a user brings; the
# on_resume hook bridges any that Orgo injects into /root/.env, and the agent /
# onboarding can also install keys at runtime. build-recipe.md §4: we do NOT use
# env:{secret}/files:secret:// (they crash the build at compile), so the secrets
# block is declarative only.
import base64
import json
import os
import ssl
import sys
import time
import urllib.request
import urllib.error

try:
    import certifi
    _SSL = ssl.create_default_context(cafile=certifi.where())
except Exception:
    _SSL = ssl.create_default_context()
    try:
        _SSL.load_default_certs()
    except Exception:
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
FILES = os.path.join(HERE, "files")
NAMESPACE = "default"
NAME = "nicks-stack"
VERSION = os.environ.get("VERSION", "0.1.2")
API_BASE = os.environ.get("ORGO_API_BASE", "https://www.orgo.ai/api")
API_KEY = os.environ.get("ORGO_API_KEY", "")

OBSIDIAN_DEB_URL = ("https://github.com/obsidianmd/obsidian-releases/releases/"
                    "download/v1.12.7/obsidian_1.12.7_amd64.deb")
OBSIDIAN_DEB_SHA = "3644e3ef19bcd23db4d17f7c73311b5245429391a2a48b361da93375f59712b0"


def rd(rel):
    with open(os.path.join(FILES, rel), "r", encoding="utf-8") as fh:
        return fh.read()


def rd_b64(rel):
    with open(os.path.join(FILES, rel), "rb") as fh:
        return base64.b64encode(fh.read()).decode("ascii")


# --------------------------------------------------------------------------
# files[]  — staged under /opt/nicks-stack/stage (copied into place post-install
# so the Hermes installer can never clobber them) + scripts/icons at final paths
# --------------------------------------------------------------------------
def F(to, body, mode="0644", when="build", owner=None, group=None):
    e = {"to": to, "inline": body, "mode": mode, "when": when}
    if owner:
        e["owner"] = owner
    if group:
        e["group"] = group
    return e


STAGE = "/opt/nicks-stack/stage"

files = [
    # --- staged Hermes config / identity / env / plugin / skills ---
    F(f"{STAGE}/hermes/config.yaml", rd("config.yaml"), "0600"),
    F(f"{STAGE}/hermes/SOUL.md", rd("SOUL.md"), "0644"),
    F(f"{STAGE}/hermes/env", rd("hermes.env"), "0600"),
    F(f"{STAGE}/hermes/plugins/observability/latitude/plugin.yaml",
      rd("plugins/observability/latitude/plugin.yaml"), "0644"),
    F(f"{STAGE}/hermes/plugins/observability/latitude/__init__.py",
      rd("plugins/observability/latitude/__init__.py"), "0644"),
    F(f"{STAGE}/hermes/skills/productivity/agent-communications-apis/SKILL.md",
      rd("skills/agent-communications-apis/SKILL.md"), "0644"),
    F(f"{STAGE}/hermes/skills/productivity/agent-communications-apis/references/agentmail-notes.md",
      rd("skills/agent-communications-apis/references/agentmail-notes.md"), "0644"),
    F(f"{STAGE}/hermes/skills/productivity/agent-communications-apis/references/agentphone-setup-notes.md",
      rd("skills/agent-communications-apis/references/agentphone-setup-notes.md"), "0644"),
    F(f"{STAGE}/hermes/skills/devops/hermes-latitude-observability/SKILL.md",
      rd("skills/hermes-latitude-observability/SKILL.md"), "0644"),
    F(f"{STAGE}/hermes/skills/payments/agent-card/SKILL.md",
      rd("skills/agent-card/SKILL.md"), "0644"),
    # --- staged Obsidian vault skeleton + vault registry ---
    F(f"{STAGE}/vault/Welcome.md", rd("vault/Welcome.md"), "0644"),
    F(f"{STAGE}/vault/.obsidian/app.json", rd("vault/.obsidian/app.json"), "0644"),
    F(f"{STAGE}/vault/.obsidian/appearance.json", rd("vault/.obsidian/appearance.json"), "0644"),
    F(f"{STAGE}/vault/.obsidian/core-plugins.json", rd("vault/.obsidian/core-plugins.json"), "0644"),
    F(f"{STAGE}/obsidian.json", rd("obsidian-registry.json"), "0644"),
    # --- wallpaper (binary → base64, decoded in the install step) ---
    F("/opt/nicks-stack/wallpaper.b64", rd_b64("wallpaper.jpg"), "0644"),
    # --- executables (installer never touches /usr/local/bin) ---
    F("/usr/local/bin/hermes-gateway-run.sh", rd("gateway-run.sh"), "0755"),
    F("/usr/local/bin/nicks-stack-onboard.sh", rd("onboard.sh"), "0755"),
    F("/usr/local/bin/nicks-stack-onboard-launch.sh", rd("onboard-launch.sh"), "0755"),
    F("/usr/local/bin/nicks-stack-telegram-pair.py", rd("telegram-pair.py"), "0755"),
    F("/usr/local/bin/nicks-stack-seed-sms-cron.py", rd("seed-sms-cron.py"), "0755"),
    F("/usr/local/bin/obsidian-launch", rd("obsidian-launch"), "0755"),
    # --- desktop icons ---
    F("/root/Desktop/Obsidian.desktop", rd("Obsidian.desktop"), "0755"),
    F("/root/Desktop/NicksStackSetup.desktop", rd("NicksStackSetup.desktop"), "0755"),
]

# --------------------------------------------------------------------------
# apps[].install — the one build-time script (runs as root, after files staged)
# --------------------------------------------------------------------------
INSTALL = f"""
set -e
export DEBIAN_FRONTEND=noninteractive
export HOME=/root
export HERMES_HOME=/root/.hermes
export PATH=/usr/local/bin:/root/.hermes/bin:/root/.hermes/node/bin:/root/.local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$PATH

# 1) Hermes Agent — non-interactive, no wizard, no Playwright (matches source VM).
#    git/ripgrep/ffmpeg are already apt-installed (build.apt), so the installer
#    takes no apt path here; Node is auto-provisioned if the base lacks it.
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash -s -- --non-interactive --skip-setup --skip-browser
hash -r || true

# 2) Global npm helpers: filesystem MCP for the Obsidian vault + agent-cards CLI.
npm install -g @modelcontextprotocol/server-filesystem@2026.1.14 agent-cards@0.5.52 \\
  || npm install -g @modelcontextprotocol/server-filesystem agent-cards

# 3) qrcode into the Hermes venv (renders the Telegram pairing QR as a PNG).
#    The venv is uv-managed and ships NO pip, so install with `uv pip`.
VENV_PY=/usr/local/lib/hermes-agent/venv/bin/python
uv pip install --python "$VENV_PY" "qrcode[pil]" \
  || /root/.hermes/bin/uv pip install --python "$VENV_PY" "qrcode[pil]" \
  || "$VENV_PY" -m pip install "qrcode[pil]" || true

# 4) Obsidian 1.12.7 (pinned) — extract the .deb (GUI deps already present via
#    Chrome); libsecret-1-0 is the only extra and pulls no libssl upgrade.
curl -fsSL "{OBSIDIAN_DEB_URL}" -o /tmp/obsidian.deb
echo "{OBSIDIAN_DEB_SHA}  /tmp/obsidian.deb" | sha256sum -c -
dpkg-deb -x /tmp/obsidian.deb /
ln -sf /opt/Obsidian/obsidian /usr/bin/obsidian
rm -f /tmp/obsidian.deb
apt-get install -y -qq --no-install-recommends libsecret-1-0 >/dev/null 2>&1 || true

# 5) Place staged Hermes config/identity/env/plugin/skills AFTER the install so
#    our files always win over anything the installer wrote.
mkdir -p /root/.hermes/plugins /root/.hermes/skills /root/.hermes/memories \\
         /root/.hermes/state /root/Documents/HermesVault /root/.config/obsidian \\
         /var/log/orgo /var/lib/orgo
cp -f  {STAGE}/hermes/config.yaml /root/.hermes/config.yaml
cp -f  {STAGE}/hermes/SOUL.md     /root/.hermes/SOUL.md
cp -f  {STAGE}/hermes/env         /root/.hermes/.env
cp -rf {STAGE}/hermes/plugins/.   /root/.hermes/plugins/
cp -rf {STAGE}/hermes/skills/.    /root/.hermes/skills/
cp -rf {STAGE}/vault/.            /root/Documents/HermesVault/
cp -f  {STAGE}/obsidian.json      /root/.config/obsidian/obsidian.json
chmod 600 /root/.hermes/config.yaml /root/.hermes/.env

# 6) Desktop wallpaper (decode the baked base64).
mkdir -p /usr/share/backgrounds
base64 -d /opt/nicks-stack/wallpaper.b64 > /usr/share/backgrounds/wallpaper.jpg

echo "nicks-stack install complete"
""".strip()

# --------------------------------------------------------------------------
# hooks
# --------------------------------------------------------------------------
ON_FIRST_BOOT = """
mkdir -p /var/lib/orgo /var/log/orgo /root/.hermes/memories /root/.hermes/state
[ -f /var/lib/orgo/nicks-stack.stamp ] || echo "nicks-stack first boot $(date -Iseconds)" > /var/lib/orgo/nicks-stack.stamp
# Lean + supervisord-safe (this also runs during the build). No hermes calls.
""".strip()

# on_resume: bridge vault secrets -> ~/.hermes/.env, seed the SMS cron, restart.
_BRIDGE_KEYS = ("COMPOSIO_CONSUMER_KEY AGENTPHONE_API_KEY AGENTPHONE_AGENT_ID "
                "AGENTPHONE_NUMBER_ID AGENTMAIL_API_KEY HERMES_LATITUDE_API_KEY "
                "HERMES_LATITUDE_PROJECT TELEGRAM_BOT_TOKEN TELEGRAM_ALLOWED_USERS "
                "TELEGRAM_HOME_CHANNEL")
ON_RESUME = f"""
# Fix any fresh-VM clock skew before the agent touches the network (SSL).
date -s "$(curl -sI http://www.google.com | awk 'tolower($1)=="date:"{{sub($1 FS,"");print}}')" 2>/dev/null || true

set -a; [ -f /root/.env ] && . /root/.env; [ -f /root/.hermes/.env ] && . /root/.hermes/.env; set +a
mkdir -p /root/.hermes /root/.hermes/state
E=/root/.hermes/.env; touch "$E"

# Bridge any Orgo-vault-injected secrets into the file Hermes actually reads.
# Idempotent strip-then-append; vault UPPER_SNAKE names == the keys config wants.
for K in {_BRIDGE_KEYS}; do
  V="$(printenv "$K" 2>/dev/null || true)"
  [ -z "$V" ] && continue
  grep -vE "^${{K}}=" "$E" > "$E.tmp" 2>/dev/null || true
  mv "$E.tmp" "$E"
  echo "${{K}}=${{V}}" >> "$E"
done
chmod 600 "$E"

# Seed the AgentPhone SMS auto-responder cron if all three params are present
# (reads them from the env we just sourced; never bakes a key).
python3 /usr/local/bin/nicks-stack-seed-sms-cron.py || true

# Restart the gateway so it re-reads .env + config (Hermes has no hot reload).
supervisorctl restart hermes-gateway 2>/dev/null || true
""".strip()

# on_every_boot: reassert the branded wallpaper (monitor-name-independent loop).
ON_EVERY_BOOT = """
export DISPLAY="${DISPLAY:-:99}"
WP=/usr/share/backgrounds/wallpaper.jpg
[ -f "$WP" ] || exit 0
for p in $(xfconf-query -c xfce4-desktop -l 2>/dev/null | grep -E 'last-image|image-path'); do
  xfconf-query -c xfce4-desktop -p "$p" -s "$WP" 2>/dev/null || true
done
xfconf-query -c xfce4-desktop -p /backdrop/screen0/monitor0/image-path -s "$WP" --create -t string 2>/dev/null || true
""".strip()

# --------------------------------------------------------------------------
# The template document
# --------------------------------------------------------------------------
template = {
    "api_version": "orgo.ai/v1",
    "template": {
        "name": NAME,
        "version": VERSION,
        "description": ("Nick's Stack — a Hermes agent on Orgo wired exactly like the "
                        "working Hubert VM: gpt-5.5 via Nous, Telegram (scan-a-QR "
                        "onboarding), Composio, AgentPhone SMS auto-responder, "
                        "AgentMail, AgentCard, Latitude tracing, and an Obsidian vault. "
                        "Bring only your own keys."),
        "publisher": "orgo",
        "license": "MIT",
        "homepage": "https://hermes-agent.nousresearch.com",
        "source": "https://github.com/NousResearch/hermes-agent",
    },
    # Modest, matches the proven-green build shape (no explicit os/gpu).
    "hardware": {
        "cpu": 2,
        "ram_gb": 4,
        "disk_gb": 20,
        "resolution": "1280x720x24",
    },
    # Declarative only (names shown in the launch UI + vault). NOT referenced via
    # {secret:} anywhere (that crashes the build); on_resume bridges whatever the
    # vault injects, and the agent/onboarding can install keys at runtime too.
    "secrets": [
        {"name": "composio_consumer_key", "optional": True,
         "description": "Composio consumer key (ck_…) — sent as the x-consumer-api-key header to the Composio MCP (connect.composio.dev/mcp). Unlocks your connected apps (Gmail, Slack, Calendar, Notion, AgentMail, …).",
         "example": "ck_...", "docs_url": "https://app.composio.dev"},
        {"name": "agentphone_api_key", "optional": True,
         "description": "AgentPhone secret key (sk_live_…) for the SMS/iMessage auto-responder cron. Pair with agentphone_agent_id + agentphone_number_id.",
         "example": "sk_live_...", "docs_url": "https://agentphone.ai"},
        {"name": "agentphone_agent_id", "optional": True,
         "description": "AgentPhone hosted agent id (POST /agents). Needed for the SMS auto-responder.",
         "example": "cm..."},
        {"name": "agentphone_number_id", "optional": True,
         "description": "AgentPhone provisioned number id (POST /agents/{id}/numbers). Needed for the SMS auto-responder.",
         "example": "cm..."},
        {"name": "agentmail_api_key", "optional": True,
         "description": "Optional direct AgentMail key (am_…). Not required if you reach AgentMail through the Composio agent_mail toolkit.",
         "example": "am_...", "docs_url": "https://agentmail.to"},
        {"name": "hermes_latitude_api_key", "optional": True,
         "description": "Latitude observability API key — enables LLM/tool tracing via the baked observability/latitude plugin. Pair with hermes_latitude_project.",
         "example": "…", "docs_url": "https://latitude.so"},
        {"name": "hermes_latitude_project", "optional": True,
         "description": "Latitude project slug (the X-Latitude-Project / service scope for your traces).",
         "example": "my-project"},
        {"name": "telegram_bot_token", "optional": True,
         "description": "Optional — the first-boot QR onboarding mints this for you. Supply a @BotFather token only if you prefer to bring your own.",
         "example": "123456789:AA...", "docs_url": "https://t.me/BotFather"},
        {"name": "telegram_allowed_users", "optional": True,
         "description": "Optional numeric Telegram user id allowlist (the QR onboarding auto-detects yours). Comma-separated.",
         "example": "123456789"},
    ],
    "build": {
        # MINIMAL + build-safe: no ca-certificates/openssl/curl (they'd upgrade
        # libssl3t64 and kill build-time supervisord). Pre-installing ripgrep +
        # ffmpeg makes the Hermes installer skip its own apt path entirely.
        "apt": ["git", "xz-utils", "python3-yaml", "ripgrep", "ffmpeg"],
    },
    "files": files,
    "apps": [
        {
            "name": "hermes-gateway",
            "title": "Hermes Gateway",
            "description": ("Hermes gateway daemon — Telegram channel, MCP connections "
                            "(Composio + Obsidian vault), and the cron scheduler "
                            "(incl. the AgentPhone SMS auto-responder)."),
            "install": INSTALL,
            "services": [
                {
                    "name": "hermes-gateway",
                    "title": "Hermes gateway",
                    "run": "/usr/local/bin/hermes-gateway-run.sh",
                    "user": "root",
                    "restart": "always",
                }
            ],
            "autostart": [
                {"run": "/usr/local/bin/nicks-stack-onboard-launch.sh", "delay": 10},
                {"run": "/usr/local/bin/obsidian-launch", "delay": 16},
            ],
        }
    ],
    "hooks": {
        "on_first_boot": ON_FIRST_BOOT,
        "on_resume": ON_RESUME,
        "on_every_boot": ON_EVERY_BOOT,
    },
    "terminal": [
        {
            "name": "hermes",
            "title": "Hermes",
            "description": "Host shell for the Hermes agent (hermes auth, logs, config).",
            "cwd": "/root",
        }
    ],
}


# --------------------------------------------------------------------------
# validate / publish / build / launch
# --------------------------------------------------------------------------
def local_validate():
    try:
        import jsonschema
    except ImportError:
        print("! jsonschema not installed — skipping local schema check "
              "(pip install jsonschema to enable)")
        return
    # Prefer a bundled/relative schema; otherwise fetch Orgo's public one so
    # this works from a standalone checkout too.
    schema = None
    for p in (os.path.join(HERE, "template-schema.json"),
              os.path.join(HERE, "..", "..", "docs", "orgo", "template-schema.json")):
        if os.path.exists(p):
            with open(p) as fh:
                schema = json.load(fh)
            break
    if schema is None:
        try:
            req = urllib.request.Request(f"{API_BASE}/template-schema")
            with urllib.request.urlopen(req, context=_SSL, timeout=20) as r:
                schema = json.loads(r.read().decode())
        except Exception as e:
            print(f"! could not load schema ({e}); skipping local check "
                  f"(use --remote-validate instead)")
            return
    jsonschema.validate(template, schema)
    print("✓ local jsonschema validation PASSED")


def _req(method, url, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Authorization": f"Bearer {API_KEY}",
                                          "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, context=_SSL) as r:
            raw = r.read().decode()
            return r.status, raw
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def remote_validate():
    st, body = _req("POST", f"{API_BASE}/templates/validate", template)
    print(f"POST /templates/validate → {st}: {body[:400]}")
    return st < 300


def publish():
    envelope = {"namespace": NAMESPACE, "name": NAME, "version": VERSION, "template": template}
    st, body = _req("POST", f"{API_BASE}/templates", envelope)
    print(f"POST /templates → {st}: {body[:400]}")
    return st < 300 or st == 409


def build_and_stream():
    st, body = _req("POST", f"{API_BASE}/templates/{NAMESPACE}/{NAME}/{VERSION}/build")
    print(f"POST …/build → {st}: {body[:200]}")
    url = f"{API_BASE}/templates/{NAMESPACE}/{NAME}/{VERSION}/build/events"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {API_KEY}"})
    print("streaming build events (SSE):")
    ok = False
    with urllib.request.urlopen(req, timeout=600, context=_SSL) as r:
        for line in r:
            s = line.decode(errors="replace").rstrip()
            if s:
                print("  " + s)
            if s.startswith("data: "):
                try:
                    event = json.loads(s.removeprefix("data: "))
                except json.JSONDecodeError:
                    event = {}
                if event.get("phase") == "ready" and event.get("level") == "success":
                    ok = True
                if event.get("phase") == "failed" or event.get("level") == "error":
                    ok = False
            if "build failed" in s or '"failed"' in s:
                ok = False
    return ok


def launch(ws_id):
    body = {"workspace_id": ws_id, "name": f"nicks-stack-test",
            "template_ref": f"{NAMESPACE}/{NAME}@{VERSION}", "ram": 4, "cpu": 2}
    st, resp = _req("POST", f"{API_BASE}/computers", body)
    print(f"POST /computers → {st}: {resp[:400]}")


def main():
    args = sys.argv[1:]
    # Always assemble + dump the resolved, inspectable artifact.
    out = os.path.join(HERE, "nicks-stack.resolved.json")
    with open(out, "w") as fh:
        json.dump(template, fh, indent=2)
    n_files = len(template["files"])
    approx = sum(len(f.get("inline", "")) for f in template["files"])
    print(f"assembled template v{VERSION}: {n_files} files, ~{approx//1024}KB inline "
          f"→ {os.path.relpath(out, HERE)}")
    local_validate()
    if "--remote-validate" in args:
        remote_validate()
    if "--publish" in args or "--build" in args:
        if not API_KEY:
            sys.exit("ORGO_API_KEY not set")
        if not publish():
            sys.exit("publish failed")
    if "--build" in args:
        if not build_and_stream():
            sys.exit("build did not reach ready")
        print("✓ build ready")
    if "--launch" in args:
        i = args.index("--launch")
        launch(args[i + 1])


if __name__ == "__main__":
    main()
