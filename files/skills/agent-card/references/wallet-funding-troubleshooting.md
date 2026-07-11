# Wallet Funding Troubleshooting

Use this when AgentCard cards fail at real merchants or Apple Pay / Google Pay wallet funding is declined.

## Diagnose the account first

Run these read-only tools in parallel:

1. `get_wallet` to check whether the live funding wallet exists and has spendable balance.
2. `list_cards` to distinguish live cards from cards marked `[TEST]` / `sandbox: true`.
3. `list_payment_methods` only when relevant to flight bookings. Saved payment methods do **not** fund the wallet or ordinary virtual cards.

Interpretation:

- An OPEN sandbox/test card with a displayed balance is not spendable at real merchants.
- A `$0.00` live wallet plus only sandbox cards means there is no live spendable AgentCard yet.
- `list_payment_methods` returning none does not explain wallet funding failure because saved methods are flight-only.

## Current wallet funding model

`fund_wallet` exposes only:

- `apple_pay`
- `google_pay`

The user selects a card inside Apple Pay or Google Pay. Funds are held in USDC after successful onramp funding. Do not tell the user to connect a Coinbase account: the AgentCard flow uses Coinbase infrastructure as an onramp but does not expose Coinbase account linking as a prerequisite or fallback.

Do not imply that raw card entry, ACH, saved Stripe cards, direct crypto deposit, or Coinbase balance transfer is available unless current tools/docs explicitly expose it.

## If every Apple Pay / Google Pay card is declined

Ask for the exact onramp error or a screenshot before diagnosing. Plausible categories include issuer decline, unsupported card type/region, identity/billing mismatch, or an AgentCard/onramp product issue, but label them as hypotheses rather than facts.

If no alternate funding rail is exposed, escalate with evidence. A concise support/vendor question should include:

- both Apple Pay and Google Pay were attempted;
- whether multiple issuers/card types were tried;
- wallet balance;
- whether existing cards are sandbox/test;
- exact error text, if available;
- a direct question about known-good issuers/card types (for example, whether Mercury debit is supported).

When escalating in a shared Slack channel, first locate the correct shared channel from existing messages or channel search, then post the concise diagnostic. Do not claim a specific issuer will work until the provider confirms it.

## Verification after a proposed fix

1. Call `get_wallet` and confirm a positive live balance.
2. Call `list_cards` and confirm the newly created card is not `sandbox: true` / `[TEST]`.
3. Only then describe it as a live spendable card.
