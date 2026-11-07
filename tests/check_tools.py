"""Offline check run by CI: the package installs, imports, and serves the tools it promises.

No network: listing tools never calls the register.
"""

import asyncio
import json
import pathlib
import tomllib

from deusproof_mcp.server import mcp

EXPECTED = {
    "birth_certificate",
    "claim_authorship",
    "certify_creation",
    "council_ballot",
    "council_vote",
    "notarize_hash",
    "prior_art_search",
    "seal_agent_card",
    "agent_card_history",
    "verify_certificate",
    "get_agent_passport",
}

root = pathlib.Path(__file__).resolve().parent.parent
tools = asyncio.run(mcp.list_tools())
names = {t.name for t in tools}
assert names == EXPECTED, f"tools changed: missing {EXPECTED - names}, extra {names - EXPECTED}"
for t in tools:
    assert (t.description or "").strip(), f"{t.name} has no description"

version = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
server = json.loads((root / "server.json").read_text(encoding="utf-8"))
assert server["version"] == version, f"server.json says {server['version']}, pyproject says {version}"
assert all(p["version"] == version for p in server["packages"]), "server.json package version differs"

print(f"ok: {len(names)} tools, version {version}")
