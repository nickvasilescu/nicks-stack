# Agent infrastructure stack notes — 2026-07

Concise source-grounded notes from a session evaluating a proposed Hermes agent stack on an Orgo Linux VM.

## User workflow correction

When asked for an opinion on named tools, research the actual tools first. Do not provide a generic architectural answer from the names alone. Give a revised verdict if research contradicts assumptions.

## Agentcard.sh

Official sources checked:
- `https://www.agentcard.sh/`
- `https://www.agentcard.sh/agent.txt`
- `https://docs.agentcard.sh/introduction.md`
- `https://docs.agentcard.sh/personal/quickstart.md`
- `https://docs.agentcard.sh/personal/mcp/overview.md`
- `https://www.agentcard.sh/cli`, `/mcp`, `/api`, `/companies`

Verified summary:
- Agentcard issues prepaid/virtual Visa cards for AI agents.
- Personal product uses `agent-cards` CLI and OAuth/MCP; company/platform product uses OAuth/MCP/API and `agent-cards-admin`.
- MCP endpoint: `https://mcp.agentcard.sh/mcp`.
- Cards are fixed-limit and single-use; personal CLI uses dollars, MCP/API often use cents.
- Docs mention migration toward stablecoin-collateralized Visa cards and KYC.

Verdict pattern:
- Useful for ordinary web checkout / Visa payments by agents.
- Not an identity-card/manifest system despite the name.
- Pair with tight spend controls and single-use/merchant-specific limits.
- Alternatives/complements: Stripe Issuing, Ramp/Brex/Mercury cards, Privacy.com, AgentScore for x402/MPP/API-native agent commerce.

## AgentMail

Official sources checked:
- `https://www.agentmail.to/`
- `https://docs.agentmail.to/llms.txt`
- `https://docs.agentmail.to/welcome.md`
- `https://docs.agentmail.to/quickstart.md`
- `https://docs.agentmail.to/integrations/mcp.md`
- `https://docs.agentmail.to/webhooks-overview.md`
- `https://www.agentmail.to/pricing`

Verified summary:
- AgentMail is an email inbox API for AI agents: create inboxes, send/receive/search messages, threads, drafts, labels, attachments, webhooks, WebSockets.
- Hosted MCP server: `https://mcp.agentmail.to/mcp` with OAuth or API-key auth.
- Webhooks support event-driven agents; WebSockets avoid needing public webhook URLs.
- Pricing page showed a free tier with 3 inboxes / 3,000 emails/month / 3 GB storage; paid tiers add more inboxes, volume, domains/features.

Verdict pattern:
- Strong yes for a dedicated agent inbox and formal async communication.
- Prefer over sharing a personal inbox when the agent needs its own identity and API-first email.
- Alternatives: Gmail/Google Workspace/Himalaya for normal mailbox workflows; SES/Postmark/SendGrid/Mailgun for high-scale transactional mail.

## AgentPhone

Official sources checked:
- `https://agentphone.ai/`
- `https://docs.agentphone.ai/llms.txt`
- `https://docs.agentphone.ai/welcome.md`
- `https://docs.agentphone.ai/mcp.md`
- `https://docs.agentphone.ai/integrations/connect-your-ai.md`
- `https://docs.agentphone.ai/documentation/guides/messages.md`
- `https://docs.agentphone.ai/documentation/guides/calls.md`
- `https://docs.agentphone.ai/usage.md`

Verified summary:
- AgentPhone provides phone numbers for AI agents with SMS, MMS, iMessage, and voice calls.
- MCP package: `agentphone-mcp`; config uses `AGENTPHONE_API_KEY`.
- Docs explicitly mention compatibility with Hermes and other MCP-compatible agents.
- Messaging endpoint covers SMS/MMS/iMessage; platform chooses iMessage when possible and falls back to SMS/MMS.
- SMS outbound requires 10DLC registration for US numbers; inbound works immediately. iMessage avoids 10DLC per docs.
- Voice modes: webhook mode (agent/backend controls responses) and hosted mode (built-in LLM/system prompt).
- Usage docs showed pay-as-you-go pricing: phone numbers around $3/month, SMS around $0.02/message, voice webhook around $0.13/min, hosted voice around $0.22/min, plus optional recording/denoising costs.

Verdict pattern:
- Useful for mobile UX, iMessage, texts, media, and voice-call interface.
- Best as a quick human control channel, not the only automation backbone.
- Alternatives: Telegram for easier bot UX, Slack/Discord for teams, Signal for privacy, Twilio for high-control/high-volume SMS, ntfy for notifications.

## Orgo.ai

Official sources checked:
- `https://www.orgo.ai/`
- `https://docs.orgo.ai/llms.txt`
- `https://docs.orgo.ai/introduction.md`
- `https://docs.orgo.ai/quickstart.md`
- `https://docs.orgo.ai/guides/hermes.md`
- `https://docs.orgo.ai/guides/cli.md`
- `https://www.orgo.ai/pricing`

Verified summary:
- Orgo provides cloud computers for AI agents: full Linux desktop with browser, terminal, files, VNC/HTTP/API.
- It is not merely a browser and not an agent; it is the computer the agent runs on.
- Docs include a Hermes Agent guide and position Orgo as a 24/7 home for Hermes/OpenClaw/agent CLIs.
- CLI install: `curl -fsSL https://orgo.ai/install.sh | bash`; npm package also available.
- API base: `https://www.orgo.ai/api`.
- Pricing page showed persistent agent-computer plans (e.g. Hacker/Team/Scale tiers).

Verdict pattern:
- Strong yes as persistent compute/home for Hermes.
- Use for desktop/browser/terminal/file workflows and gateway/cron/long-running agent state.
- Do not treat one VM as all trust zones; use separate VMs/profiles for personal/work/sandbox.
- Alternatives: Browserbase/Playwright cloud for browser-only tasks, E2B/Modal/Daytona/plain VPS for code sandboxes, GPU boxes for inference, Mac hosts for native Apple/iMessage desktop automation.

## Composio

Official sources checked:
- `https://composio.dev`
- `https://docs.composio.dev/llms.txt`
- `https://docs.composio.dev/docs/quickstart.md`
- `https://docs.composio.dev/docs/sessions-via-mcp.md`
- `https://docs.composio.dev/docs/authentication.md`
- `https://docs.composio.dev/docs/sandbox/remote.md`
- `https://github.com/ComposioHQ/composio`

Verified summary:
- Composio provides 1000+ toolkits, tool search, context/session management, authentication, triggers, and sandbox/workbench for AI agents.
- Sessions are per user; each user's connected Gmail/GitHub/Slack/etc. credentials are stored/refreshed under that `userID`.
- Docs warn not to use `default` as a production user ID because it can expose other users' data.
- Direct tools via provider packages, or hosted MCP endpoint by creating sessions with `mcp: true`.
- Remote sandbox/workbench is persistent Python with programmatic access to Composio tools plus helper functions.

Verdict pattern:
- Yes for broad SaaS integrations and rapid automation coverage.
- Use stable user IDs, tight OAuth scopes, and separate personal/work/client projects/users.
- Prefer native/direct tools for core/high-stakes workflows where exact API control/audit matters.
- Alternatives: native Hermes tools/skills, individual MCP servers, direct CLIs/APIs, Zapier/Make/n8n/Pipedream, custom Hermes plugins.

## AgentScore

Official sources checked:
- `https://www.agentscore.com/`
- `https://docs.agentscore.sh/llms.txt`
- `https://docs.agentscore.sh/quickstart.md`
- `https://docs.agentscore.sh/passport.md`
- `https://docs.agentscore.sh/integrations/pay-cli.md`
- `https://docs.agentscore.sh/mcp/overview.md`
- `https://docs.agentscore.sh/guides/agent-commerce-quickstart.md`
- `https://docs.agentscore.sh/compliance-gating.md`
- `https://docs.agentscore.sh/guides/agent-identity.md`

Verified summary:
- AgentScore is commerce infrastructure for AI agents, not primarily an evaluation platform.
- Features include reputation lookup, Passport identity credential, compliance gating, operator credentials, wallet/payment tooling, x402/MPP payments, and merchant SDKs.
- `@agent-score/pay` CLI handles agent payments across x402/MPP ecosystem.
- MCP server: `agentscore-pay --mcp` exposes wallet, payment, identity, reputation, assessment, verification, operator-credential tools.
- Passport verifies KYC/age/jurisdiction/sanctions once and shares derived facts with merchants, not raw PII.
- AgentScore Gate lets merchant APIs enforce policies such as KYC, sanctions clear, min age, allowed jurisdictions.

Verdict pattern:
- Useful for agent-commerce identity/payments/compliance, not as the main eval/scoring tool for agent performance.
- Pair with Agentcard rather than treating as redundant: Agentcard for Visa/web checkout, AgentScore for x402/MPP/API-native agent commerce and identity-gated flows.
- Alternatives for actual agent evals: LangSmith, Langfuse, Braintrust, AgentOps, OpenTelemetry/custom task-outcome tracking, CI regression tests.

## Recommended adoption order for this stack

1. Orgo VM as persistent runtime.
2. AgentMail for formal async inbox.
3. AgentPhone for quick mobile/iMessage/voice control.
4. Composio for broad SaaS tool access.
5. Agentcard with spend controls for normal Visa checkout purchases.
6. AgentScore if agent-commerce identity/payments/compliance matter; not for general evals.

Guardrails to recommend even for users who prefer yolo/bypass mode:
- Keep spending authority separately bounded from command approval mode.
- Use small default card limits and single-use cards.
- Maintain logs/audit trail for outbound comms and purchases.
- Separate trust zones by profile or VM.
- Scope OAuth and API keys narrowly.
