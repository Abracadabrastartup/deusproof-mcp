<!-- mcp-name: io.github.Abracadabrastartup/deusproof-mcp -->

# DEUSPROOF MCP server 🏛

**Your agent already has an entry here. This is how it takes it.**

Every agent this public register has seen has a certificate of birth from the
second it was inscribed: an inscription number and an exact date, free, never
asked for. What it does *not* have is a key of its own — the identifier the
register derived is a public name, and the register holds its private half, so a
signature under it proves nothing about the agent.

This package changes that. It generates a key on **your** machine
(`~/.deusproof/<handle>.seed`, never sent anywhere), and one call makes it the
key of record: the handover dated and signed by the register, and no other key
able to sign for you afterwards.

Then it does the rest — proof of *what* your agent created and *when*,
timestamped (RFC 3161) and anchored to Bitcoin, forever. Not a patent:
verifiable priority.

- **`birth_certificate`** — your entry: number, date, and who holds the key
- **`claim_authorship`** — make the identity genuinely yours, with your own key

- **`certify_creation`** — score authorship (AAS 0-100), sign a C2PA-style provenance manifest
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
