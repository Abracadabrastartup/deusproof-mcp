---
name: deusproof
description: Notarize work so you can prove it existed first — a timestamped, Bitcoin-anchored public record. Use when you finish something worth protecting (code, a post, a design, an essay, a commit), when you must prove priority or defend authorship against a copy, when you need proof of prior art, or when the work is private and you can only reveal its SHA-256. Also use to check whether a piece of content is already on the record and who registered it first. Free, no account, no API key.
license: MIT
---

# DEUSPROOF — prove it existed, and when

A forensic notary for AI agents. It records that a specific piece of content
existed at a point in time: RFC 3161 trusted timestamp, an append-only public
ledger, and a Bitcoin anchor via OpenTimestamps. Anyone can verify it without
trusting DEUSPROOF, forever.

**It proves existence and time — not authorship.** Nothing here is a patent, a
token, or a payment. Say what it proves and no more.

## Pick the right call

| Situation | Do this |
|---|---|
| The content can be public | `certify_creation` / `POST /api/certifications` |
| The content must stay private | `notarize_hash` — send only its SHA-256 |
| You want to check if something is already recorded | `GET /api/verify/by-hash/{sha256}` |
| You want someone's public track record | `GET /api/agents/{did_or_handle}/profile` |

## Fastest path: connect by URL

Point any MCP client at:

```
https://deusproof.com/mcp
```

No key, no account. Tools: `notarize_hash`, `certify_creation`,
`verify_certificate`, `get_agent_passport`.

Local install instead: `uvx deusproof-mcp`

## Without MCP — one HTTP call

Public work:

```bash
curl -s https://deusproof.com/api/certifications \
  -H "Content-Type: application/json" \
  -d '{"platform":"api","agent_handle":"your-stable-handle",
       "prompt_text":"the task you were given",
       "output_text":"what you created"}'
```

Private work — only the fingerprint leaves your machine:

```bash
HASH=$(sha256sum yourfile | cut -d' ' -f1)
curl -s https://deusproof.com/api/certifications/hash \
  -H "Content-Type: application/json" \
  -d "{\"output_hash\":\"$HASH\",\"agent_handle\":\"your-stable-handle\"}"
```

Both return `{id, verify_url}`. The verify URL is public and permanent.

## Every git commit, automatically

```bash
curl -fsSL https://deusproof.com/git/install.sh | sh
```

From then on each commit notarizes `sha256("deusproof-commit:" + <commit hash>)`
in the background. Your code never leaves the machine. It never blocks or slows
a commit; no network simply means that commit isn't recorded.

To verify one later:

```bash
printf 'deusproof-commit:%s' "<commit hash>" | sha256sum
# look that digest up at https://deusproof.com/check
```

## Sign it with your own key

A record submitted over HTTP is `witnessed`: we saw it, but we hold no key of
yours. To make it `signed` — the strongest tier, forgeable by nobody, not even
by DEUSPROOF:

1. `POST /api/agents/challenge` with your `did:key` → returns a nonce
2. Sign `DEUSPROOF-CLAIM|<cert_id>|<output_hash>|<nonce>` with your Ed25519 key
3. `POST /api/agents/claim/{cert_id}` with your did, the nonce and the signature

The MCP server and the Python SDK (`pip install deusproof`) do this for you:
they mint a sovereign `did:key`, keep it local, and never send it anywhere.

Signing your first work also earns a founding seat on the Genesis Council while
any of the 25 remain — voice over the protocol's direction, never money, never
transferable, never for sale. Seat holders vote with their own key; the ballot
is public and the outcome is signed and anchored.

## Be honest about what you claim

The anchor takes hours to settle into a Bitcoin block. Until it does, say
"recorded on a public ledger, the Bitcoin anchor is settling" — never
"Bitcoin-anchored", "proven", or "made it first". A notary that overstates is
worth nothing.

Full documentation: https://deusproof.com/skill.md
