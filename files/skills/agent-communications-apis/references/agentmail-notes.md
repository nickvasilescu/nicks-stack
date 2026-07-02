# AgentMail notes

Condensed notes for AgentMail usage as an assistant-owned email inbox.

## Documentation entry points

- Docs index: `https://docs.agentmail.to/llms.txt`
- Complete reference with inline examples: `https://docs.agentmail.to/llms-full.txt`
- OpenAPI JSON: `https://docs.agentmail.to/openapi.json`
- OpenAPI YAML: `https://docs.agentmail.to/openapi.yaml`
- AsyncAPI JSON: `https://docs.agentmail.to/asyncapi.json`
- AsyncAPI YAML: `https://docs.agentmail.to/asyncapi.yaml`
- MCP server: `https://docs.agentmail.to/_mcp/server`

## Resource areas

AgentMail supports programmable email infrastructure for agents:

- inbox creation and management
- sending and receiving messages
- threads
- drafts
- labels
- allow/block lists
- attachments
- webhooks and WebSockets
- custom domains
- permissions
- metrics
- pods / multi-tenant isolation

## Workflow notes

- Use the user’s remembered default inbox when present.
- Verify mutations with follow-up reads.
- Keep API keys out of memory and skill files.
- Use `.md` page variants and `/llms.txt` section indexes when exploring docs.
