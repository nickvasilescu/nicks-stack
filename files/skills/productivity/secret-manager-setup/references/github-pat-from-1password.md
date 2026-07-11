# GitHub PAT from 1Password (Dewey)

When private GitHub is needed and env looks empty:

1. Do **not** stop at `# GITHUB_TOKEN` commented in `~/.hermes/.env`.
2. Ensure `OP_SERVICE_ACCOUNT_TOKEN` is loaded from `.env`.
3. Read field only: `op read 'op://Hermes/Hermes Agent Secrets/GITHUB_PAT'`.
4. Metadata: classic `ghp_` (~40 chars) or `github_pat_…`; reject len-36 UUID.
5. Vendor test: `GET https://api.github.com/user` with Bearer → 200; note `login` (e.g. `nickvasilescu`).
6. Clone: `git clone --depth 1 https://x-access-token:${TOKEN}@github.com/OWNER/REPO.git`
7. Scrub temp token files; never dump full `op item get --format=json` into chat.

Map both `GITHUB_TOKEN` and `GH_TOKEN` to the same PAT field after vendor success.

Primary internal product repo for pricing/RAM: **`OrgoAI/orgo-web`** → skill `orgo-cloud-computers` → `references/pricing-and-ram-limits.md`.
