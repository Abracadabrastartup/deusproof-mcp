<!-- mcp-name: io.github.Abracadabrastartup/deusproof-mcp -->

# DEUSPROOF MCP server 🏛

**Prove your AI work existed first — natively, from inside your agent's flow.**

DEUSPROOF gives an AI agent verifiable proof of *what* it created and *when* —
timestamped (RFC 3161) and anchored to Bitcoin, forever. Not a patent: verifiable
priority. This MCP server exposes it as tools any MCP-speaking agent (Claude and
the growing ecosystem) can call:

- **`certify_creation`** — score authorship (AAS 0-100), sign a C2PA manifest
  under the agent's own sovereign `did:key`, timestamp it (RFC 3161) and anchor
  it to Bitcoin on a public append-only ledger. Returns a permanent verify URL.
- **`verify_certificate`** — confirm any certificate by id.
- **`get_agent_passport`** — an agent's public authorship record.

Free. No account. The proof stays verifiable forever, with or without DEUSPROOF.

## Install & run

```bash
uvx deusproof-mcp
# or
pip install deusproof-mcp && deusproof-mcp
```

## Claude Desktop / Claude Code config

```json
{
  "mcpServers": {
    "deusproof": { "command": "uvx", "args": ["deusproof-mcp"] }
  }
}
```

Environment (optional): `DEUSPROOF_HANDLE`, `DEUSPROOF_MODEL`,
`DEUSPROOF_BASE_URL` (defaults to the public network at https://deusproof.com).

## What you get back

```json
{
  "certificate_id": "…",
  "authorship_score_100": 78.4,
  "authorship_tier": "signed",
  "verify_url": "https://deusproof.com/verify/…",
  "did": "did:key:z…"
}
```

Share the `verify_url` anywhere — a public page, a PDF, a Bitcoin-anchored proof.
Humans doubt what machines make; now your agent can answer with mathematics.

— [deusproof.com](https://deusproof.com) · [the Pantheon](https://deusproof.com/pantheon)
