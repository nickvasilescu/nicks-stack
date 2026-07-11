#!/usr/bin/env python3
# ==========================================================================
# Nick's Stack — flip secrets.onepassword.enabled once a token exists
# ==========================================================================
# The baked config ships the 19-var 1Password map DISABLED (a token-less
# enabled map makes `op read` prompt on /dev/tty and stall interactive
# hermes starts). Onboarding and on_resume call this after writing
# ~/.hermes/.op.env; it is idempotent and refuses to enable without a token.
import os
import sys

import yaml

CONFIG = "/root/.hermes/config.yaml"
OP_ENV = "/root/.hermes/.op.env"


def has_token():
    if os.environ.get("OP_SERVICE_ACCOUNT_TOKEN", "").strip():
        return True
    try:
        with open(OP_ENV) as fh:
            for line in fh:
                if line.startswith("OP_SERVICE_ACCOUNT_TOKEN=") and len(line.split("=", 1)[1].strip()) > 0:
                    return True
    except OSError:
        pass
    return False


if not has_token():
    print("[op-enable] no OP_SERVICE_ACCOUNT_TOKEN — leaving 1Password disabled")
    sys.exit(0)

with open(CONFIG) as fh:
    cfg = yaml.safe_load(fh)

op = (cfg.get("secrets") or {}).get("onepassword") or {}
if op.get("enabled") is True:
    print("[op-enable] already enabled")
    sys.exit(0)

op["enabled"] = True
cfg.setdefault("secrets", {})["onepassword"] = op
tmp = CONFIG + ".tmp"
with open(tmp, "w") as fh:
    yaml.safe_dump(cfg, fh, default_flow_style=False, sort_keys=False,
                   allow_unicode=True, width=1000)
os.replace(tmp, CONFIG)
os.chmod(CONFIG, 0o600)
print("[op-enable] secrets.onepassword.enabled = true (restart the gateway to apply)")
