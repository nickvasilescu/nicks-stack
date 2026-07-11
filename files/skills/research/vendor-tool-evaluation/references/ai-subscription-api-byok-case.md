# AI subscription, API billing, and BYOK compatibility case

## Reusable decision test

For any request to move a paid AI plan into an IDE or third-party client, answer three independent questions:

1. Does the consumer subscription explicitly include developer API credits?
2. If an API key can be created under the same login, is API billing still separate?
3. Does the destination currently accept that provider and key type as BYOK?

A “no” at either step 1 or step 3 blocks the proposed transfer. The existence of a shared account or API-key page does not prove transferable entitlement.

## Worked case: SuperGrok Heavy to Cursor

Checked 2026-07-09. Re-verify before relying on provider lists or roadmap claims.

### Upstream entitlement

xAI’s API account FAQ says a Grok account and xAI API account may share sign-in details, but explicitly states that billing is separate for Grok and the xAI API:

- https://docs.x.ai/console/faq/accounts

The API billing page describes API consumption as separately funded through prepaid credits or monthly invoicing:

- https://docs.x.ai/console/billing

The API quickstart instructs users to load the API account with credits and then generate an API key:

- https://docs.x.ai/developers/quickstart

Conclusion: SuperGrok consumer limits are not xAI API credits and cannot pay for third-party API calls.

### Destination compatibility

Cursor’s current BYOK documentation lists OpenAI, Anthropic, Google, Azure OpenAI, and AWS Bedrock. It does not list xAI:

- https://cursor.com/help/models-and-usage/api-keys

A Cursor staff response also explicitly said xAI was not supported as BYOK and distinguished Cursor’s built-in Grok integration from user-supplied xAI keys:

- https://forum.cursor.com/t/xai-api-problem/152455/3

Conclusion: purchasing separate xAI API credits would not enable the key in Cursor while xAI remains unsupported there.

### Built-in model versus BYOK

Cursor may expose Grok through its own model picker and usage pool. That is a Cursor-provided integration, not a bridge to SuperGrok subscription limits:

- https://cursor.com/docs/models

### Recommended user action

- Do not recommend buying API credits until destination support is confirmed.
- If the model is built into the destination, explain whose plan or usage pool pays for it.
- If the consumer subscription was purchased solely for the unsupported transfer, recommend prompt cancellation, downgrade, or a refund request without promising eligibility.

## Research lesson

The decisive source was not the consumer pricing page. It was the account FAQ’s explicit separation of identity and billing, followed by the destination’s supported-provider list. Use third-party search systems for discovery and corroboration, but cite the first-party billing and compatibility pages for the verdict.
