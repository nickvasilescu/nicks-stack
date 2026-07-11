# Telegram managed QR onboarding reference

Concrete pattern for Hermes Telegram bot creation via managed QR **and** the reliable BotFather fallback used when QR fails on live calls.

## When to use

- User wants: “give me a QR I can scan to create/connect the bot”
- Customer pilot desk needs a scannable desktop poster
- Prefer managed flow for desk prep; keep BotFather path ready for live calls

## Relevant installed code

- `hermes_cli.telegram_managed_bot.create_pairing(bot_name=...)`
- `render_qr_terminal` / `poll_pairing_result_once` / `is_valid_telegram_bot_token`
- `hermes_cli.config.save_env_value`
- Onboarding API: `https://setup.hermes-agent.nousresearch.com` (`TELEGRAM_ONBOARDING_URL` override)

## Critical: expiry

Managed pairings often expire in **~5 minutes**. API returns HTTP **410** with `{"status":"expired"}`.

If the customer creates a bot after expiry, Telegram may show a bot but Hermes **never receives the token**. Symptoms:

- No `TELEGRAM_BOT_TOKEN` in `.env`
- Gateway: `No messaging platforms enabled`
- Customer: `/start` or `Hey` does nothing

**Fix:** regenerate pairing immediately before scan, or switch to BotFather manual.

## Pairing + desktop QR poster

```bash
HERMES_PY=/usr/local/lib/hermes-agent/venv/bin/python
$HERMES_PY -m pip install -q 'qrcode[pil]' pillow
$HERMES_PY - <<'PY'
import json, sys
from pathlib import Path
sys.path.insert(0, '/usr/local/lib/hermes-agent')
from hermes_cli.telegram_managed_bot import create_pairing
import qrcode
from PIL import Image, ImageDraw

pairing = create_pairing(bot_name='Budgetdog Ops')
if not pairing:
    raise SystemExit('PAIRING_CREATE_FAILED')
state = {
    'pairing_id': pairing.pairing_id,
    'poll_token': pairing.poll_token,
    'suggested_username': pairing.suggested_username,
    'deep_link': pairing.deep_link,
    'qr_payload': pairing.qr_payload,
    'expires_at': pairing.expires_at,
}
Path('/root/.hermes/tmp/telegram_pairing.json').write_text(json.dumps(state, indent=2))
# public status without secrets
Path('/root/BudgetdogOps/telegram/status.json').write_text(json.dumps({
    'status': 'waiting_for_scan',
    'suggested_username': pairing.suggested_username,
    'deep_link': pairing.deep_link,
    'expires_at': pairing.expires_at,
}, indent=2))
qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=12, border=2)
qr.add_data(pairing.qr_payload); qr.make(fit=True)
img = qr.make_image(fill_color='black', back_color='white').convert('RGB')
img.save('/root/Desktop/SCAN_ME_Telegram.png')
# optional branded poster for VNC; open with feh -F
print(pairing.deep_link, pairing.expires_at)
PY
```

Always show: expiry time, deep link fallback, Refresh-QR launcher.

## Poller → save env → start gateway

Poll while user scans and taps **Create Bot**. On ready:

1. `save_env_value('TELEGRAM_BOT_TOKEN', result.token)` (never print)
2. Username / `TELEGRAM_ALLOWED_USERS` / `TELEGRAM_HOME_CHANNEL` from `owner_user_id` when present
3. Start gateway with env loaded:

```bash
pkill -f 'hermes gateway' 2>/dev/null || true
set -a; source /root/.hermes/.env; set +a
nohup hermes gateway run --accept-hooks >> /root/customer-logs/gateway.log 2>&1 &
```

4. Verify with redacted `getMe` + process check + log line `telegram connected`

## BotFather manual fallback (preferred on live calls if QR flaky)

1. Customer: `@BotFather` → `/newbot` → name + username ending in `bot`
2. Paste token to operator (ephemeral) or type into box:

```bash
~/scripts/configure_telegram_manual.sh '<TOKEN>' '<owner_telegram_user_id>'
# or
# save_env_value + start gateway as above
```

3. Owner ID from managed result or `@userinfobot`
4. Customer DMs bot: `hi`

## Validation checklist (required before “all set”)

1. `.env` has `TELEGRAM_BOT_TOKEN`
2. Allowlist or explicit open/pairing policy
3. `TELEGRAM_HOME_CHANNEL` if cron/notifications expected
4. Gateway process running
5. Logs: `✓ telegram connected` / `Gateway running with 1 platform(s)`
6. `getMe` returns expected username (redacted)
7. Real inbound message + outbound reply observed when possible

## Notes

- Display name free text; username unique + ends in `bot`
- Never reuse operator/Dewey bot on a customer box
- Groups need privacy off or admin; DMs simpler
- Do not print tokens
