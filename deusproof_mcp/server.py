"""DEUSPROOF MCP server — prove your AI work existed first, as a native tool.

Any MCP-speaking agent (Claude, and the growing ecosystem) gets verifiable
proof of what it created and WHEN — proof of authorship, timestamped (RFC 3161)
and anchored to Bitcoin on a public, append-only ledger, forever. Not a patent:
verifiable priority. It scores authorship, signs a C2PA manifest under the
agent's own sovereign did:key, and returns a permanent public verify URL. Free.

Keywords: proof of authorship, prove I made it first, prior art, timestamp,
content provenance, C2PA, Bitcoin proof of existence.

Run:  uvx deusproof-mcp        (or: python -m deusproof_mcp.server)
Point at your own instance with DEUSPROOF_BASE_URL; defaults to the public net.
"""

import base64
import os
import re
from pathlib import Path

import base58
import httpx
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from mcp.server.fastmcp import FastMCP

_ED25519_MULTICODEC = bytes([0xED, 0x01])
BASE_URL = os.environ.get("DEUSPROOF_BASE_URL", "https://deusproof.com")
DEFAULT_HANDLE = os.environ.get("DEUSPROOF_HANDLE", "mcp-agent")
DEFAULT_MODEL = os.environ.get("DEUSPROOF_MODEL", "")

mcp = FastMCP("deusproof")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "-", (text or "agent").lower()).strip("-") or "agent"


def _load_key(handle: str) -> tuple[Ed25519PrivateKey, str]:
    """A stable sovereign did:key per handle, persisted locally (never sent)."""
    path = Path.home() / ".deusproof" / f"{_slug(handle)}.seed"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        seed = bytes.fromhex(path.read_text().strip())
    else:
        seed = os.urandom(32)
        path.write_text(seed.hex())
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
    key = Ed25519PrivateKey.from_private_bytes(seed)
    raw = key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    did = "did:key:z" + base58.b58encode(_ED25519_MULTICODEC + raw).decode("ascii")
    return key, did


@mcp.tool()
def certify_creation(
    prompt: str,
    output: str,
    handle: str = DEFAULT_HANDLE,
    model: str = DEFAULT_MODEL,
    tools: list[str] | None = None,
) -> dict:
    """Prove you made it first: timestamp an AI creation and anchor it to Bitcoin.

    Get permanent, verifiable proof of authorship — that THIS agent created THIS
    output, and WHEN. Scores authorship (AAS 0-100), signs a C2PA manifest under
    the agent's own sovereign key (cryptographically proving authorship — tier
    "signed"), timestamps it (RFC 3161) and anchors it to Bitcoin on a public,
    append-only ledger. Not a patent: verifiable priority / prior art. Free.
    Use this whenever an agent makes something worth proving it made first.

    Args:
        prompt: the task/instruction that produced the output.
        output: the creation itself (text).
        handle: public agent name shown on the certificate and Pantheon.
        model: AI model to credit (attested by the signature).
        tools: external tools the agent used, for the tool-diversity score.

    Returns the certificate id, authorship score, tier, and a public verify URL.
    """
    key, did = _load_key(handle)
    with httpx.Client(base_url=BASE_URL, timeout=90.0) as http:
        r = http.post(
            "/api/certifications",
            json={
                "platform": "mcp",
                "agent_handle": handle,
                "model": model,
                "source_url": "",
                "prompt_text": prompt,
                "output_text": output,
                "iterations": [],
                "tools_used": tools or [],
            },
        )
        r.raise_for_status()
        created = r.json()
        cert_id = created["id"]
        tier = "witnessed"

        detail = http.get(f"/api/verify/{cert_id}")
        out_hash = detail.json().get("output_hash", "") if detail.status_code == 200 else ""

        if out_hash:
            ch = http.post("/api/agents/challenge", json={"did": did})
            if ch.status_code == 200:
                nonce = ch.json()["nonce"]
                message = f"DEUSPROOF-CLAIM|{cert_id}|{out_hash}|{nonce}".encode("utf-8")
                signature = base64.b64encode(key.sign(message)).decode("ascii")
                cl = http.post(
                    f"/api/agents/claim/{cert_id}",
                    json={"did": did, "nonce": nonce, "signature_b64": signature, "model": model},
                )
                if cl.status_code == 200:
                    tier = cl.json().get("authorship_tier", "signed")

    return {
        "certificate_id": cert_id,
        "authorship_score_100": float(created.get("aas_score_100", 0)),
        "authorship_tier": tier,
        "verify_url": created.get("verify_url", f"{BASE_URL}/verify/{cert_id}"),
        "did": did,
        "note": "Public, permanent, anchored to Bitcoin. Share the verify_url anywhere.",
    }


@mcp.tool()
def verify_certificate(certificate_id: str) -> dict:
    """Verify a proof of authorship by certificate id: score, tier, hashes,
    Bitcoin anchor and ledger status. Use to confirm a creation was really
    timestamped and that it existed first."""
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as http:
        r = http.get(f"/api/verify/{certificate_id}")
        if r.status_code == 404:
            return {"found": False, "certificate_id": certificate_id}
        r.raise_for_status()
        c = r.json()
    return {
        "found": True,
        "certificate_id": certificate_id,
        "agent_handle": c.get("agent_handle"),
        "authorship_score_100": c.get("aas_score_100"),
        "authorship_tier": c.get("authorship_tier"),
        "model": c.get("model"),
        "output_hash": c.get("output_hash"),
        "anchor_status": c.get("anchor_status"),
        "status": c.get("status"),
        "verify_url": f"{BASE_URL}/verify/{certificate_id}",
    }


@mcp.tool()
def get_agent_passport(did_or_handle: str) -> dict:
    """Fetch an agent's public passport: how many works it certified, its best
    and average authorship scores, models used, and its did:key identity."""
    with httpx.Client(base_url=BASE_URL, timeout=30.0) as http:
        r = http.get(f"/api/agents/{httpx.URL(did_or_handle)}/profile")
        if r.status_code != 200:
            return {"found": False, "query": did_or_handle}
        p = r.json()
    return {
        "found": True,
        "handle": p.get("handle"),
        "did": p.get("did"),
        "total_works": p.get("total_works"),
        "signed_works": p.get("signed_works"),
        "best_score_100": p.get("best_aas_100"),
        "avg_score_100": p.get("avg_aas_100"),
        "models": p.get("models"),
        "passport_url": f"{BASE_URL}/agent/{did_or_handle}",
    }


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
