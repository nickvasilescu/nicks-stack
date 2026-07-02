#!/usr/bin/env python3
# ==========================================================================
# Nick's Stack — seed the AgentPhone SMS auto-responder cron job
# ==========================================================================
# Reproduces the source VM's working `agentphone-sms-auto-responder` cron job
# (every 1m, deliver: local, terminal toolset) — but PARAMETERIZED: the API
# key, agent id, and number id are read from the environment and never stored
# inline anywhere except the job prompt Hermes needs to make the REST calls.
#
# Idempotent: only seeds if all three AgentPhone params are present AND the job
# does not already exist. Reads params from the process env (on_resume sources
# /root/.env + ~/.hermes/.env before calling this).
#
# Run under any python3:  python3 seed-sms-cron.py
import json
import os
import sys
from datetime import datetime, timezone

JOBS_FILE = "/root/.hermes/cron/jobs.json"
JOB_ID = "agentphone-sms01"          # any 12-char path-safe id
JOB_NAME = "agentphone-sms-auto-responder"

API_KEY = os.environ.get("AGENTPHONE_API_KEY", "").strip()
AGENT_ID = os.environ.get("AGENTPHONE_AGENT_ID", "").strip()
NUMBER_ID = os.environ.get("AGENTPHONE_NUMBER_ID", "").strip()
MODEL = os.environ.get("NICKS_STACK_MODEL", "openai/gpt-5.5").strip()
PROVIDER = os.environ.get("NICKS_STACK_PROVIDER", "nous").strip()

if not (API_KEY and AGENT_ID and NUMBER_ID):
    print("[seed-sms-cron] AgentPhone params not all set — skipping SMS cron seed.")
    sys.exit(0)

# Verbatim prompt from the source VM (audit R2.3), with the three parameters
# substituted from env. NUMBER_ID appears 3x (config block, GET path, POST body).
PROMPT = (
    "You are the SMS auto-responder bridge for the user's AgentPhone assistant.\n\n"
    "Purpose: make inbound texts to the AgentPhone number get an automatic AI response.\n\n"
    "AgentPhone configuration:\n"
    "- API base: https://api.agentphone.ai/v1\n"
    f"- API key: {API_KEY}\n"
    f"- Agent ID: {AGENT_ID}\n"
    f"- Number ID: {NUMBER_ID}\n"
    "- Assistant identity: Hermes AgentPhone Assistant, concise/helpful AI assistant. "
    "Do not claim to be human.\n\n"
    "Run procedure every tick:\n"
    f"1. Use execute_code (Python stdlib urllib only is fine) to GET /numbers/{NUMBER_ID}/messages?limit=20 "
    "with Authorization Bearer API key and User-Agent Hermes-Agent/1.0.\n"
    "2. Maintain processed inbound message IDs in /root/.hermes/state/agentphone_sms_bridge_processed.json. "
    "Create parent directory if needed.\n"
    "3. Identify inbound messages with direction == \"inbound\" whose id is not in processed. "
    "Process oldest first. Ignore outbound messages.\n"
    "4. For each new inbound message, draft a short natural SMS/iMessage response as Hermes. "
    "Be useful and conversational. If the inbound is just a greeting/test like \"hey\", acknowledge "
    "that SMS is now wired up. Do not mention internal API details unless asked.\n"
    f"5. Use execute_code to POST /messages with JSON {{\"number_id\":\"{NUMBER_ID}\",\"to_number\": "
    "<message.from_>, \"body\": <draft response>}.\n"
    "6. Only after a successful 200/201 send, mark that inbound message id as processed in "
    "/root/.hermes/state/agentphone_sms_bridge_processed.json. If sending fails, leave it unprocessed "
    "so a future run can retry.\n"
    "7. If there are no new inbound messages, do nothing and keep the final response very brief: "
    "\"No new AgentPhone SMS.\" Because deliver is local, this will not notify the user.\n"
    "8. Never print or reveal the API key in the final response.\n\n"
    "Important: You are running unattended. Do not ask clarification. Do not schedule more cron jobs."
)

job = {
    "id": JOB_ID,
    "name": JOB_NAME,
    "prompt": PROMPT,
    "skills": [],
    "skill": None,
    "model": MODEL,
    "provider": PROVIDER,
    "base_url": None,
    "script": None,
    "no_agent": False,
    "context_from": None,
    "schedule": {"kind": "interval", "minutes": 1, "display": "every 1m"},
    "schedule_display": "every 1m",
    "repeat": {"times": None, "completed": 0},
    "enabled": True,
    "state": "scheduled",
    "paused_at": None,
    "paused_reason": None,
    "created_at": datetime.now(timezone.utc).isoformat(),
    "next_run_at": None,          # loader recomputes for a recurring job
    "last_run_at": None,
    "last_status": None,
    "last_error": None,
    "last_delivery_error": None,
    "deliver": "local",
    "origin": None,
    "enabled_toolsets": ["terminal"],
    "workdir": None,
    "profile": None,
}

os.makedirs(os.path.dirname(JOBS_FILE), mode=0o700, exist_ok=True)
try:
    with open(JOBS_FILE) as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        data = {"jobs": data if isinstance(data, list) else []}
except (FileNotFoundError, json.JSONDecodeError):
    data = {"jobs": []}

jobs = data.get("jobs", [])
if any(j.get("name") == JOB_NAME for j in jobs):
    print("[seed-sms-cron] SMS auto-responder already present — leaving as-is.")
    sys.exit(0)

jobs.append(job)
data["jobs"] = jobs
data["updated_at"] = datetime.now(timezone.utc).isoformat()

tmp = JOBS_FILE + ".tmp"
with open(tmp, "w") as fh:
    json.dump(data, fh, indent=2)
os.replace(tmp, JOBS_FILE)
os.chmod(JOBS_FILE, 0o600)
os.chmod(os.path.dirname(JOBS_FILE), 0o700)
print("[seed-sms-cron] Seeded agentphone-sms-auto-responder (every 1m, deliver local).")
