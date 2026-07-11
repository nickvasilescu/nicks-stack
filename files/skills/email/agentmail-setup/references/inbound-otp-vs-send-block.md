# Inbound OTP vs outbound send-block

When the user asks “is this the same bounce issue?” about a missing third-party OTP:

## Same (use send-block fix)

- Error is on **our** send: `MessageRejectedError` 403 `Recipient(s) blocked … bounced`
- `GET /v0/lists/send/block/{email}` returns 200 with `reason: bounced`
- Fix: DELETE entry if address known-good; resend; capture messageId

## Different (not send-block)

- Mail is **expected inbound** to an AgentMail address (OTP, fund verification, vendor notice)
- Other messages from the same vendor **already land**
- `receive/block` empty for that address
- No outbound 403 on our side

→ Product never sent / separate verification channel. AgentMail list DELETE will not help.

## AgentCard example (2026-07)

- SMS phone verify OK; KYC approved; TEST cards live
- `fund_wallet` still wants email OTP; no fund OTP in `${AGENTMAIL_INBOX}`
- Card/access/KYC/WorkOS messages **did** arrive
- Conclusion: not Michael-style send-block; see `managed-hermes-on-orgo` → `references/agentcard-fund-otp-vs-bounce.md`
