# AgentCard Wallet Funding (post-KYC)

Use when the user wants to fund the AgentCard wallet, or when `fund_wallet` fails after identity verification looks complete.

## Correct funding path

1. Orient with `whoami`, `get_kyc_status`, `get_wallet`, `get_plan`, `list_cards`.
2. If KYC is not approved, finish KYC first (`references/agentcard-kyc-troubleshooting.md`).
3. Ensure cardholder phone + terms: `submit_user_info(phone_number E.164, terms_accepted=true)` after explicit user confirmation of phone and terms. Dewey default phone for account flows: `+15555550123` only when the user confirms.
4. Ask for dollar amount (and Apple Pay vs Google Pay if it matters). Convert dollars to cents (`$50` → `5000`). Range: $2–$10,000.
5. Call `fund_wallet(amount_cents, payment_method?)`. Success should return an Apple Pay / Google Pay **checkout URL** for the user to open. Then poll `get_wallet` after they pay.
6. Do **not** create cards as a probe for funding health. `create_card` can succeed in sandbox while the live wallet stays unfundable.

## Split gates (common confusion)

These are separate systems. Any one can pass while another blocks:

| Signal | Meaning |
|--------|---------|
| `get_kyc_status` verified / `whoami` KYC approved | Identity verification done |
| `submit_user_info` saved | Phone + cardholder terms stored |
| `get_wallet` status active, balance $0 | Wallet provisioned; not proof onramp works |
| `fund_wallet` returns checkout URL | Live onramp ready; user still must complete Pay sheet |
| `list_cards` entries with `[TEST]` / `sandbox: true` | Sandbox cards only; not real merchant spend |

Stripe `setup_payment_method` is for **flights only**. It does not fund the wallet or virtual cards.

## KYC approved but `fund_wallet` still says verification required

Observed 2026-07-09 (Dewey / `${AGENTMAIL_INBOX}`):

- `whoami`: KYC verified, account active
- `get_kyc_status`: verified / approved; `start_kyc` nextStep verified
- `submit_user_info`: phone + terms saved
- `get_wallet`: active, $0
- `fund_wallet` (Apple Pay and Google Pay, $50): repeated
  `Verification is required before funding the wallet` + stale guidance to complete verification / `submit_user_info`
- `create_card` still issued **sandbox/TEST** cards (e.g. last4 3103) without wallet balance
- Support (`start_support_chat`) confirmed **backend issue**: onramp blocked / live issuance not activating despite verified KYC; escalated to engineering

### What to do

1. Confirm once that phone + terms are saved and KYC is approved (do not re-collect SSN/docs).
2. Retry `fund_wallet` once after `submit_user_info` if phone was missing.
3. If still blocked with approved KYC + saved phone/terms, **stop retry loops**. Open support with the template below. Do not invent alternate funding APIs.
4. Tell the user clearly: wallet is not fundable until AgentCard unblocks the onramp; sandbox cards are not a substitute for live spend.
5. Optionally poll `read_support_chat` later and re-try `fund_wallet` after support says fixed.

### Support template (funding onramp stuck)

```text
Wallet funding blocked despite KYC approved.

Account: <email> (user id from whoami)
whoami: KYC verified / account active
get_kyc_status: verified=true status=approved
submit_user_info: phone + terms saved
get_wallet: active, balance $0.00
fund_wallet (amount_cents=..., apple_pay and/or google_pay): returns "Verification is required before funding the wallet" even after phone+terms saved and KYC approved.
create_card issues sandbox/TEST cards while live wallet remains unfundable.

Please unlock wallet onramp / Apple Pay Google Pay funding, or state any remaining verification step. Do not need SSN or document details resent.
```

## Sandbox / TEST cards

- New accounts often start in test/sandbox issuing. Docs mention CLI `agent-cards mode` / MCP `get_mode`+`set_mode`; those mode tools may be missing from a given MCP tool list even when docs list them.
- Sandbox cards: marked `[TEST]` / `sandbox: true` in `list_cards`; numbers often start `4242…`; no real charges; not usable at real merchants; do not count toward Free plan monthly card quota.
- Live cards require wallet funds + working onramp; they draw on wallet balance when used.
- **Never** call `create_card` without user-confirmed amount. Diagnostic create_card still creates a real TEST card entry and emails the user.

## Safety / UX

- Confirm amount and payment method before `fund_wallet`.
- Confirm phone and terms before `submit_user_info`.
- Confirm amount before any `create_card` (including "just testing").
- Never display PAN/CVV unless the user explicitly asks.
- Do not store SSN, document numbers, or raw ID images in memory or support text.
