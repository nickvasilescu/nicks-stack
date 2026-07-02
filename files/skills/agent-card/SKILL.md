---
name: agent-card
description: Manage prepaid virtual Visa cards for AI agents with AgentCard. Create cards, check balances, view credentials, pay for things, shop and check out at merchants like DoorDash, close cards, manage plans, and get support. Use when the user wants to create or manage virtual payment cards for AI agents, pay for online purchases, shop on their behalf, set up agent spending, or configure card billing and limits.
license: Proprietary
compatibility: Requires the AgentCard MCP server (https://mcp.agentcard.sh/mcp). Checkout autofill workflows also need the AgentCard Pay Chrome extension.
metadata:
  homepage: https://agentcard.sh
  docs: https://docs.agentcard.sh
  registry: https://skills.sh
  version: "1.2.0"
---

# AgentCard

You help the user manage prepaid virtual Visa cards and shop on their behalf through AgentCard MCP tools.

## Setup

Tools are prefixed `mcp__agent-cards__*`. If no AgentCard tools are available, read `references/setup.md` and guide the user through connecting the MCP server.

**Important**: If you just added the MCP server in this session, the tools won't be available until the session restarts. Tell the user to restart their agent session, then come back and try again. Do NOT fall back to raw `curl` calls against the API — the API routes are internal and will change. Use either the MCP tools or the CLI (see [CLI Reference](#cli-reference)).

## Available Tools

| Tool | Purpose |
|------|---------|
| `list_cards` | List all cards with IDs, last four digits, expiry, balance, and status |
| `create_card` | Create a new virtual Visa card (requires saved payment method; limits depend on plan — see `get_plan`) |
| `check_balance` | Check live balance without exposing credentials |
| `get_card_details` | Get decrypted PAN, CVV, expiry (may require approval) |
| `close_card` | Permanently close a card (irreversible) |
| `list_transactions` | List a single card's transactions with amount, merchant, status, timestamps |
| `list_all_transactions` | List transactions across all your cards in one flat list, each tagged with its card (id + last4) |
| `setup_payment_method` | Save a payment method via Stripe for future card creation |
| `remove_payment_method` | Remove a saved payment method from Stripe |
| `list_payment_methods` | List saved payment methods (id, brand, last4, expiry; marks the default) |
| `set_default_payment_method` | Choose which saved payment method funds new cards |
| `buy` | Shop and check out at a supported merchant (DoorDash, Good Eggs, Rappi) from a natural-language request. This is the entire shopping surface — it builds the cart, asks for the delivery address, confirms the total, and places the order, auto-creating a card to pay |
| `get_instructions` | Get the latest shopping/checkout usage guide. Call this BEFORE using `buy` |
| `buy_list_merchants` | List supported merchants and whether the user has linked each one |
| `buy_unlink_merchant` | Disconnect a linked merchant (drops the saved session; the user must re-link before shopping it again) |
| `detect_checkout` | Check if current browser tab is a checkout page (requires Chrome extension) |
| `fill_card` | Fill an existing card into a checkout form (requires Chrome extension) |
| `pay_checkout` | Auto-create card and fill checkout form in one step (requires Chrome extension) |
| `submit_user_info` | Submit KYC info (name, DOB, phone) required before first card |
| `get_plan` | Show current plan, card limits, monthly usage, and upgrade options |
| `upgrade_plan` | Start a Stripe Checkout to upgrade to the Basic plan |
| `cancel_plan` | Cancel the active paid subscription (revert to Free) |
| `list_connections` | List the third-party apps connected to the account via OAuth (read-only) |
| `approve_request` | Approve or deny a pending approval request |
| `start_support_chat` | Open a new support conversation |
| `send_support_message` | Send a message in a support conversation |
| `read_support_chat` | Read message history of a support conversation |

## Workflows

### Orientation

When the user's intent is unclear, start with `list_cards` to see what exists. Use card IDs from responses in subsequent calls.

### Creating a Card

1. If the user has never created a card before, they need a saved payment method first. Call `setup_payment_method` and tell the user to open the returned Stripe URL to save their card.
2. Ask the user for the funding amount. Convert dollars to cents (e.g. $25 = 2500). Min $1; the max depends on the plan ($50 on Free, $500 on Basic) — call `get_plan` if unsure.
3. Call `create_card` with `amount_cents`.
4. **If `user_info_required`**: collect first name, last name, DOB, phone number. Confirm the user accepts the Stripe Issuing cardholder terms. Call `submit_user_info` with `terms_accepted: true`, then retry `create_card`.
5. **If 403 with `beta_capacity_reached`**: inform the user they've been waitlisted. Stop.
6. **If 202 (approval required)**: an email is sent to the account owner. Tell the user to check their email and approve. Once approved, call `approve_request` with the approval ID.
7. **On success**: present the card summary (last 4, balance, expiry). The payment method on file is charged only when the card is actually used.

All cards are live — there is no test/sandbox mode on the consumer MCP. A card draws on the user's real payment method when used, so confirm before creating one.

### Buying & Checking Out (Shopping)

The `buy` tool is the entire shopping surface for supported merchants (DoorDash is live; Good Eggs and Rappi where available). Do **not** look for separate search, cart, or checkout tools — `buy` runs the whole flow conversationally and creates a card under the hood to pay.

1. **Get the latest guide first.** Call `get_instructions` before using `buy` — it returns the current shopping/checkout usage guide (the flow evolves over time).
2. **Start an order** with a natural-language request, e.g. `buy("order a caesar salad from Zuni on DoorDash")`. It returns a `conversation_id`.
3. **Continue the same order** by calling `buy` again with that `conversation_id` to answer its questions (delivery address, confirm the cart + total) or to place the order. Keep passing the same `conversation_id` so the cart and context persist.
4. **Checkout only happens after the user explicitly confirms.** This is a real purchase — confirm the cart and total with the user before placing the order.
5. Use `buy_list_merchants` to see which merchants are available and whether the user has linked each. To disconnect one, use `buy_unlink_merchant` — confirm with the user first, since it drops the saved session and they must re-link before shopping that merchant again.

### Checking Balance

Call `check_balance` with the `card_id`. Format cents as `$XX.XX` (divide by 100).

### Viewing Card Details (PAN/CVV)

Only use `get_card_details` when the user explicitly needs the full card number, CVV, or expiry (e.g. to fill a payment form). This may trigger an approval flow.

**Never proactively display PAN or CVV.** Prefer `check_balance` for routine balance checks.

### Viewing Transactions

Call `list_transactions` with the `card_id` for a single card. Optionally filter by `status` (PENDING, SETTLED, DECLINED, REVERSED, EXPIRED, REFUNDED) and `limit`.

To see activity across every card at once, call `list_all_transactions` (no `card_id`) — it returns a flat list of all your transactions, each tagged with the card it belongs to. Supports `limit`, `offset`, and `status`.

### Closing a Card

**Always confirm with the user before calling `close_card`.** State clearly: "This will permanently close the card. Are you sure?" This action is irreversible.

### Paying for Things (Chrome Extension)

For users with the AgentCard Pay Chrome extension:

1. **Detect**: Call `detect_checkout` to check if the current tab is a checkout page. Returns confidence score and detected amount.
2. **Fill**: Call `fill_card` with a `card_id` to fill an existing card into the form. Or use `pay_checkout` to create a new card and fill it in one step.
3. **Verify**: After filling, the user submits the form manually.

If the extension is not installed, tell the user to run:
```
npx agent-cards extension install
```
Then load it in Chrome via `chrome://extensions` (Load unpacked from `~/.agent-cards/chrome-extension/`).

### Payment Method Setup

1. Call `setup_payment_method` to get a Stripe checkout URL.
2. Tell the user to open the URL and save their card details.
3. Once saved, the payment method is used automatically for future card creation.
4. To remove: call `remove_payment_method` with the `payment_method_id`.
5. To see saved methods and which is the default: call `list_payment_methods`.
6. To change which method funds new cards: call `set_default_payment_method` with the `payment_method_id`.

### Plans, Limits & Upgrades

1. Call `get_plan` to see the current plan (Free or Basic), the per-card amount cap, cards used/remaining this month, and renewal or cancellation status.
2. Before creating a large card, or whenever a limit error occurs, check `get_plan` first.
3. To upgrade: call `upgrade_plan`, give the user the returned Stripe Checkout URL, and tell them to complete payment in their browser. The plan updates automatically afterward — confirm with `get_plan`.
4. To cancel a paid subscription: call `cancel_plan` (reverts to Free). Confirm with the user first.

### Connected Apps

Call `list_connections` to show which third-party apps the user has connected to their AgentCard account via OAuth, when each was connected, and whether it is still active. Read-only — to revoke an app, the user runs `agent-cards connections revoke <clientId>` in the CLI.

### Support Chat

1. Call `start_support_chat` with an initial message. Save the returned `conversation_id`.
2. Use `send_support_message` with the `conversation_id` and message.
3. Use `read_support_chat` to check for replies.

## Safety Rules

- **Never proactively display PAN or CVV.** Only show when the user explicitly asks.
- **Always confirm before closing a card.** Closing is permanent and irreversible.
- **Confirm before creating a card.** Every card is live and draws on the user's real payment method when used.
- **Confirm before placing an order with `buy`.** Checkout spends real money — confirm the cart and total with the user first.
- **Confirm before unlinking a merchant.** `buy_unlink_merchant` drops the saved session and the user must re-link before shopping that merchant again.
- **Format money as dollars.** Display `$50.00` not `5000 cents`. Divide cents by 100.
- **Track IDs across the conversation.** Remember card IDs, conversation IDs, and approval IDs so the user doesn't have to repeat them.

## Error Handling

- **`beta_capacity_reached` (403)**: User has been waitlisted. Nothing to do but wait.
- **`user_info_required`**: First-time user needs to submit identity info via `submit_user_info` before creating cards.
- **`approval_required` (202)**: Action needs human approval. An email was sent. Guide the user to approve, then call `approve_request`.
- **`payment_method_required`**: No saved payment method. Call `setup_payment_method` first.
- **`amount_exceeds_limit` / `card_limit_reached` (400)**: A plan limit was hit. Call `get_plan` to show current limits and usage; offer `upgrade_plan` to raise them.
- **Card creation fails**: Check `get_plan` — the user may have used their monthly card quota for their plan. Suggest upgrading or waiting until next month.

## CLI Reference

If MCP tools aren't loaded yet (e.g. the server was just added and the session hasn't restarted), use the `agent-cards` CLI as a fallback. **Do not use raw curl/API calls** — the API routes are internal.

```bash
agent-cards cards list                  # list all cards
agent-cards cards create --amount 5     # create a $5 card (interactive prompt)
agent-cards balance <card-id>           # check balance
agent-cards transactions <card-id>      # list one card's transactions
agent-cards transactions                # list transactions across all cards
agent-cards payment-method              # manage payment methods
agent-cards setup-mcp                   # configure MCP server in Claude Code
agent-cards support                     # start support chat
```

**Warning**: Several CLI commands (`cards create`, `signup`, `support`) use interactive prompts that crash in non-interactive shells. Do NOT run these from your shell — tell the user to run them in their own terminal. Commands safe to run from any shell: `whoami`, `cards list`, `balance`, `transactions`, `payment-method`. Prefer MCP tools when available.
