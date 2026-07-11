# Agent-commerce checkout failure localization

Use this when an agent can browse, build a cart, and confirm a total, but checkout repeatedly fails with a generic merchant or buy-assistant error.

## Evidence-first phase localization

Map observed artifacts to the commerce lifecycle:

1. Account and identity gate
2. Wallet or funding gate
3. One-time card mint
4. Merchant tokenization or payment-method attachment
5. Order submission
6. Issuer authorization
7. Settlement and confirmation

Collect read-only evidence before retrying:

- Account status and KYC state
- Wallet balance and status
- Plan limits, remaining order entitlement, and remaining card quota
- Merchant link/session status
- Cards created during each attempt: live vs sandbox, amount, status, timestamps
- Account-wide and per-card transactions, including declined and pending authorizations
- Merchant order history, if its read path still works
- Exact conversation/order identifier and raw tool error

## High-value inference pattern

If each attempt:

- successfully mints a live card sized to the confirmed total plus a small buffer,
- then closes that card,
- produces no settled, pending, or declined card transaction,
- and produces no merchant order,

then the strongest diagnosis is: **the failure occurred after card minting but before issuer authorization**, usually during merchant tokenization, session-bound checkout, anti-bot handling, response parsing, or order submission.

Do not call this an issuer decline or insufficient-funds problem without a recorded authorization/decline. A closed unspent card often reflects deliberate compensation after pre-placement failure.

If a later read-only order-history request fails with the same buy-assistant error, increase the probability of a shopping-service or conversation-state failure rather than a card-specific problem.

## Retry discipline

Before every retry, verify whether a failed attempt consumed:

- monthly card quota,
- lifetime/free-order entitlement,
- wallet reservation,
- merchant cart state.

Do not keep blind-retrying when each attempt mints and closes a new card. Repeated retries can exhaust card quota even when no purchase occurs. Prefer:

1. Stop after repeated identical compensated failures.
2. Verify no transaction and no merchant order.
3. Preserve all attempt/card/conversation IDs.
4. Escalate for the raw backend or merchant error.
5. Ask support to restore quota consumed by failed compensated attempts.
6. Only then reconnect the merchant session or start a fresh shopping conversation, depending on the returned cause.

Use an idempotency key for retries whenever the merchant surface exposes one. A generic assistant-level retry is not proof that the same idempotency key was preserved.

## Grounding sources and interpretation

Prefer this evidence order:

1. Live account/card/transaction state
2. Merchant order history
3. Official product lifecycle and troubleshooting docs
4. Official status and incident activity
5. Official changelog/update history
6. Exa, Firecrawl, Perplexity, and live social reports

A green public status page does not rule out a merchant-adapter, shopping-worker, or conversation-specific failure if those components are not listed separately. Conversely, low historical uptime may be distorted by stale incidents; inspect incident activity before inferring a current outage.

## Support escalation payload

Include:

- account identifier,
- merchant and order summary,
- confirmed total and tip,
- conversation/order IDs,
- every generated card ID, last four digits, spend limit, status, and timestamp,
- wallet/KYC/plan/link state,
- transaction search result,
- exact error text,
- whether diagnostic reads also fail,
- explicit requests for the failing phase, raw backend/merchant error, no-order/no-charge confirmation, and quota restoration.

Never include PAN, CVV, bearer tokens, OTPs, or private keys.