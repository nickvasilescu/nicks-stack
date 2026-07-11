#!/usr/bin/env python3
"""Bootstrap or verify an agent-readable Obsidian vault.

Stdlib-only. Creates missing directories and starter Markdown files, but never
overwrites existing notes.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from textwrap import dedent

MAJOR_FOLDERS = [
    "01.Agent Operating System",
    "02.Current Projects",
    "03.Research Pipeline",
    "04.People and Organizations",
    "05.Tools and Systems",
    "06.SOPs and Skills",
    "07.Capture",
    "90.Archive",
    "attachments",
]

SUBDIRS = [
    "02.Current Projects/04.Archive",
    "03.Research Pipeline/inbox",
    "03.Research Pipeline/sources",
    "03.Research Pipeline/synthesis",
    "03.Research Pipeline/briefs",
    "03.Research Pipeline/entities",
    "03.Research Pipeline/contradictions",
    "04.People and Organizations/people",
    "04.People and Organizations/organizations",
    "06.SOPs and Skills/Archived",
    "07.Capture/voice-notes",
    "07.Capture/ideas",
    "07.Capture/scratch",
]

ROOT_INDEX = """# Agent Knowledge Vault Index

This vault is the canonical human-readable knowledgebase for Hermes and other agents. It is a library and operating manual, not hot memory and not a secret store. Read `SCHEMA.md` for source, confidence, and archive conventions.

## Folder Map

| Folder | Purpose | Start Here |
|---|---|---|
| `01.Agent Operating System/` | Hermes identity, permissions, memory policy, tools, security | `01.Agent Operating System/INDEX.md` |
| `02.Current Projects/` | Active projects, open loops, decisions | `02.Current Projects/INDEX.md` |
| `03.Research Pipeline/` | Raw sources, synthesis, briefs, entities, contradictions | `03.Research Pipeline/INDEX.md` |
| `04.People and Organizations/` | People and organization notes | `04.People and Organizations/INDEX.md` |
| `05.Tools and Systems/` | Agent tools, infrastructure, services | `05.Tools and Systems/INDEX.md` |
| `06.SOPs and Skills/` | Human-readable SOPs and candidate Hermes skills | `06.SOPs and Skills/INDEX.md` |
| `07.Capture/` | Raw voice notes, ideas, and scratch capture | `07.Capture/INDEX.md` |
| `90.Archive/` | Historical material only | `90.Archive/INDEX.md` |

## Rules for Hermes

- Read the relevant `INDEX.md` before editing inside a major folder.
- Prefer canonical files listed in indexes.
- Do not search `90.Archive/` unless historical context is explicitly needed.
- Do not store secrets, API keys, passwords, or payment details in this vault.
- If a folder becomes confusing, update its `INDEX.md`.
"""

SCHEMA = """# SCHEMA

This file defines conventions for the agent-readable Obsidian vault.

## Knowledge Layers

- Hermes `memory`: compact durable facts and user preferences.
- Hermes skills: reusable procedures.
- `session_search`: transcript archive with receipts.
- This vault: human-readable operating manual, project library, and research wiki.

## Source Rules

- Every factual research note should include source URLs or file references.
- Use confidence labels: `[verified]`, `[likely]`, `[unverified]`, `[conflicting]`.
- Put unresolved conflicts in `03.Research Pipeline/contradictions/`.

## Tags

Start minimal. Add tags only when repeated retrieval needs prove they help.

## Archive Rule

Archive material is historical. Do not treat it as current unless the task asks for history.
"""

INDEXES = {
    "01.Agent Operating System/INDEX.md": """# Agent Operating System Index

This folder holds Hermes operating context: identity-adjacent notes, permissions, memory policy, tool stack, and security model.

## Canonical Files

| File | Purpose |
|---|---|
| `01.Hermes.md` | Hermes setup and operating assumptions |
| `02.Permissions.md` | What the agent can do without asking |
| `03.Memory Policy.md` | What goes in memory, skills, sessions, or vault |
| `04.Tool Stack.md` | Tools, integrations, providers, profiles |
| `05.Security Model.md` | Boundaries, secrets, channels, approvals |

## Where To Go

- Start with `03.Memory Policy.md` when deciding where knowledge belongs.
- Start with `04.Tool Stack.md` when configuring or troubleshooting integrations.
- Start with `05.Security Model.md` before changing trust or payment boundaries.
""",
    "02.Current Projects/INDEX.md": """# Current Projects Index

This folder holds active projects, open loops, and decisions.

## Canonical Files

| File | Purpose |
|---|---|
| `01.Active Projects.md` | Current project list and status |
| `02.Open Loops.md` | Questions, blockers, and follow-ups |
| `03.Decisions.md` | Durable decisions with dates and rationale |

## Rules for Hermes

- Prefer these canonical files before creating project sprawl.
- Move stale project notes into `04.Archive/`.
""",
    "03.Research Pipeline/INDEX.md": """# Research Pipeline Index

This folder supports file-based Scout -> Analyst -> Briefer workflows.

## Folder Map

| Folder | Purpose |
|---|---|
| `inbox/` | Raw findings from scouts or capture jobs |
| `sources/` | Processed source pages and documents |
| `synthesis/` | Analyst notes and cross-source synthesis |
| `briefs/` | Delivered or draft briefings |
| `entities/` | People, companies, products, concepts |
| `contradictions/` | Conflicts and unresolved claims |

## Rules for Hermes

- Do not analyze inside `inbox/`; preserve source text and URLs.
- Put confidence labels on synthesized claims.
- Move processed raw files only after synthesis is written.
""",
    "04.People and Organizations/INDEX.md": """# People and Organizations Index

This folder holds notes about people and organizations.

## Folder Map

| Folder | Purpose |
|---|---|
| `people/` | Individual people |
| `organizations/` | Companies, labs, customers, vendors, communities |

## Rules for Hermes

- Keep sensitive personal data out unless the user explicitly requests it.
- Link people to organizations with Obsidian wikilinks when useful.
""",
    "05.Tools and Systems/INDEX.md": """# Tools and Systems Index

This folder holds notes about agent tools, accounts, services, and infrastructure.

## Canonical Files

| File | Purpose |
|---|---|
| `AgentMail.md` | Agent email setup and conventions |
| `AgentPhone.md` | Agent phone/iMessage setup and conventions |
| `Agentcard.md` | Agent payment-card notes and boundaries |
| `AgentScore.md` | Agent scoring/evaluation notes |
| `Composio.md` | Composio tool-use notes |
| `Orgo VM.md` | Orgo/Linux VM notes |
| `Mem0.md` | External memory provider notes |

## Rules for Hermes

- Store operational notes here, not secrets.
- Link exact official docs when commands or setup steps matter.
""",
    "06.SOPs and Skills/INDEX.md": """# SOPs and Skills Index

This folder holds human-readable SOPs and candidate Hermes skills.

## Canonical Files

| File | Purpose |
|---|---|
| `SOPs.md` | Procedures that are useful to read but not yet skills |
| `Skill Ideas.md` | Workflows that may deserve a Hermes skill |

## Rules for Hermes

- Turn repeated successful procedures into Hermes skills.
- Do not keep stale SOPs and skills with contradictory instructions.
""",
    "07.Capture/INDEX.md": """# Capture Index

This folder holds raw capture before it is filed elsewhere.

## Folder Map

| Folder | Purpose |
|---|---|
| `voice-notes/` | Raw or cleaned voice notes |
| `ideas/` | Early ideas before evaluation |
| `scratch/` | Temporary notes and workpads |

## Rules for Hermes

- Preserve raw capture when it may matter.
- Promote useful capture into canonical folders; do not let this become a second archive.
""",
    "90.Archive/INDEX.md": """# Archive Index

This folder holds historical material only.

## Rules for Hermes

- Do not search this folder unless the user asks for historical context.
- Do not treat archived notes as current state.
- If archived material informs a new decision, cite it and write the current decision elsewhere.
""",
}

FILES = {
    "01.Agent Operating System/01.Hermes.md": "# Hermes\n\nCurrent Hermes setup notes and operating assumptions.\n",
    "01.Agent Operating System/02.Permissions.md": "# Permissions\n\nDocument what the agent can do without asking, what requires confirmation, and what is forbidden.\n",
    "01.Agent Operating System/03.Memory Policy.md": "# Memory Policy\n\nUse `memory` for compact durable facts, skills for procedures, `session_search` for transcript receipts, and this vault for readable reference.\n",
    "01.Agent Operating System/04.Tool Stack.md": "# Tool Stack\n\nDocument Hermes tools, providers, profiles, messaging channels, MCP servers, and integrations.\n",
    "01.Agent Operating System/05.Security Model.md": "# Security Model\n\nDocument trusted channels, secrets boundaries, payment boundaries, account separation, and approval rules.\n",
    "02.Current Projects/01.Active Projects.md": "# Active Projects\n\nList current projects here.\n",
    "02.Current Projects/02.Open Loops.md": "# Open Loops\n\nTrack questions, blockers, and follow-ups here.\n",
    "02.Current Projects/03.Decisions.md": "# Decisions\n\nRecord durable decisions with date, rationale, and source links.\n",
    "05.Tools and Systems/AgentMail.md": "# AgentMail\n\nOperational notes only. Do not store credentials.\n",
    "05.Tools and Systems/AgentPhone.md": "# AgentPhone\n\nOperational notes only. Do not store credentials.\n",
    "05.Tools and Systems/Agentcard.md": "# Agentcard\n\nOperational notes and payment boundaries only. Do not store card details.\n",
    "05.Tools and Systems/AgentScore.md": "# AgentScore\n\nEvaluation/scoring notes.\n",
    "05.Tools and Systems/Composio.md": "# Composio\n\nTool-use notes and setup references.\n",
    "05.Tools and Systems/Orgo VM.md": "# Orgo VM\n\nLinux VM setup and operational notes.\n",
    "05.Tools and Systems/Mem0.md": "# Mem0\n\nExternal semantic memory notes. Keep Obsidian as readable source of truth, not a duplicate of every memory fact.\n",
    "06.SOPs and Skills/SOPs.md": "# SOPs\n\nHuman-readable procedures that may later become Hermes skills.\n",
    "06.SOPs and Skills/Skill Ideas.md": "# Skill Ideas\n\nRepeated workflows that may deserve Hermes skills.\n",
}


def write_missing(path: Path, content: str, dry_run: bool) -> str:
    if path.exists():
        return f"exists {path}"
    if dry_run:
        return f"would-create {path}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dedent(content).strip() + "\n", encoding="utf-8")
    return f"created {path}"


def expected_paths(root: Path) -> list[Path]:
    """Return required paths for the detected vault layout.

    The default bootstrap layout uses the original compact starter structure.
    Staged rebuilds may use the Dewey V2 structure, which adds Operations,
    Raw Imports, Migration Reports, and moves People/Research/SOPs to their
    V2 positions. Detect that layout and verify it without forcing duplicate
    compatibility folders into the staged vault.
    """
    if (root / "07.Operations").exists() or (root / "08.SOPs and Skills").exists():
        v2_paths = [
            "INDEX.md",
            "SCHEMA.md",
            "AGENTS.md",
            "HERMES.md",
            "00.Migration Reports",
            "00.Migration Reports/INDEX.md",
            "00.Migration Reports/Cutover Checklist.md",
            "00.Migration Reports/Legacy Path Map.md",
            "01.Agent Operating System",
            "01.Agent Operating System/INDEX.md",
            "01.Agent Operating System/Hermes Operating Rules.md",
            "01.Agent Operating System/Memory Policy.md",
            "01.Agent Operating System/Tool Stack.md",
            "02.Current Projects",
            "02.Current Projects/INDEX.md",
            "02.Current Projects/Active Projects.md",
            "02.Current Projects/Open Loops.md",
            "02.Current Projects/Decisions.md",
            "03.People and Organizations",
            "03.People and Organizations/INDEX.md",
            "03.People and Organizations/People",
            "04.Research Pipeline",
            "04.Research Pipeline/INDEX.md",
            "04.Research Pipeline/Sources",
            "04.Research Pipeline/Synthesis",
            "04.Research Pipeline/Briefs",
            "05.Tools and Systems",
            "05.Tools and Systems/INDEX.md",
            "05.Tools and Systems/Hermes.md",
            "05.Tools and Systems/Obsidian.md",
            "05.Tools and Systems/Composio.md",
            "06.Capture",
            "06.Capture/INDEX.md",
            "06.Capture/Daily",
            "07.Operations",
            "07.Operations/INDEX.md",
            "07.Operations/Finance",
            "07.Operations/Finance/INDEX.md",
            "07.Operations/Private",
            "07.Operations/Private/INDEX.md",
            "08.SOPs and Skills",
            "08.SOPs and Skills/INDEX.md",
            "08.SOPs and Skills/SOPs.md",
            "08.SOPs and Skills/Skill Ideas.md",
            "90.Archive",
            "90.Archive/INDEX.md",
            "99.Raw Imports",
            "99.Raw Imports/INDEX.md",
            "99.Raw Imports/Compiled-Vaults",
            "attachments",
        ]
        return [root / p for p in v2_paths]

    paths: list[Path] = [root / "INDEX.md", root / "SCHEMA.md"]
    paths.extend(root / d for d in MAJOR_FOLDERS)
    paths.extend(root / d for d in SUBDIRS)
    paths.extend(root / p for p in INDEXES)
    paths.extend(root / p for p in FILES)
    return paths


def build(root: Path, dry_run: bool) -> None:
    if not dry_run:
        root.mkdir(parents=True, exist_ok=True)
    else:
        print(f"would-create {root}")

    for folder in MAJOR_FOLDERS + SUBDIRS:
        path = root / folder
        if path.exists():
            print(f"exists {path}")
        elif dry_run:
            print(f"would-create {path}")
        else:
            path.mkdir(parents=True, exist_ok=True)
            print(f"created {path}")

    print(write_missing(root / "INDEX.md", ROOT_INDEX, dry_run))
    print(write_missing(root / "SCHEMA.md", SCHEMA, dry_run))

    for rel, content in INDEXES.items():
        print(write_missing(root / rel, content, dry_run))
    for rel, content in FILES.items():
        print(write_missing(root / rel, content, dry_run))


def check(root: Path) -> int:
    missing = [p for p in expected_paths(root) if not p.exists()]
    issues: list[str] = []

    index = root / "INDEX.md"
    if index.exists():
        text = index.read_text(encoding="utf-8", errors="replace")
        for token in ["Folder Map", "Rules for Hermes", "90.Archive", "SCHEMA.md"]:
            if token not in text:
                issues.append(f"INDEX.md missing token: {token}")
    else:
        issues.append("INDEX.md missing")

    schema = root / "SCHEMA.md"
    if schema.exists():
        text = schema.read_text(encoding="utf-8", errors="replace")
        for token in ["confidence", "session_search", "skills", "memory"]:
            if token not in text:
                issues.append(f"SCHEMA.md missing token: {token}")
    else:
        issues.append("SCHEMA.md missing")

    if missing or issues:
        print(f"FAIL {root}")
        if missing:
            print("Missing paths:")
            for p in missing:
                print(f"- {p}")
        if issues:
            print("Issues:")
            for item in issues:
                print(f"- {item}")
        return 1

    print(f"PASS {root}")
    print("Required indexes, SCHEMA.md, major folders, and starter canonical files are present.")
    return 0


def default_vault() -> str:
    return os.environ.get("OBSIDIAN_VAULT_PATH") or os.environ.get("WIKI_PATH") or str(Path.home() / "agent-knowledge")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bootstrap or verify an agent-readable Obsidian vault.")
    parser.add_argument("vault", nargs="?", default=default_vault(), help="Vault path; defaults to OBSIDIAN_VAULT_PATH, WIKI_PATH, or ~/agent-knowledge.")
    parser.add_argument("--check", action="store_true", help="Verify required vault structure and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be created without writing files.")
    args = parser.parse_args()

    root = Path(args.vault).expanduser().resolve()
    if args.check:
        return check(root)
    build(root, args.dry_run)
    return 0


if __name__ == "__main__":
    sys.exit(main())
